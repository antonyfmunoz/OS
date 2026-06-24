"""Peripheral scanner — enumerates all connected peripherals.

Runs at daemon startup and on-demand via rescan. Uses WMI/PowerShell on
Windows, stubs on other platforms. Results are cached for 60s to avoid
repeated expensive WMI calls.

Each scanner function returns a list of dicts matching the Peripheral.to_dict()
wire format. The scanner runs on the daemon (nodes/), the Peripheral dataclass
lives in transports/ — we return plain dicts to avoid cross-layer import.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 60


@dataclass
class ScanResult:
    peripherals: list[dict[str, Any]] = field(default_factory=list)
    scanned_at: float = 0.0

    @property
    def age_s(self) -> float:
        if self.scanned_at == 0:
            return float("inf")
        return time.monotonic() - self.scanned_at

    @property
    def stale(self) -> bool:
        return self.age_s > _CACHE_TTL_S


_cached_result = ScanResult()


def scan_all_peripherals(force: bool = False) -> list[dict[str, Any]]:
    """Run full peripheral scan. Returns list of Peripheral-shaped dicts.

    Uses cached result if <60s old unless force=True.
    """
    global _cached_result
    if not force and not _cached_result.stale:
        return _cached_result.peripherals

    peripherals: list[dict[str, Any]] = []
    if sys.platform == "win32":
        peripherals.extend(_scan_monitors())
        peripherals.extend(_scan_audio_devices())
        peripherals.extend(_scan_cameras())
        peripherals.extend(_scan_input_devices())
        peripherals.extend(_scan_storage())
        peripherals.extend(_scan_network_interfaces())
        peripherals.extend(_scan_display_adapters())
        peripherals.extend(_scan_bluetooth())
    # Linux/macOS stubs — dispatch point for future implementation

    _cached_result = ScanResult(
        peripherals=peripherals,
        scanned_at=time.monotonic(),
    )
    return peripherals


def get_scan_age_s() -> float:
    """Return age of the cached scan result in seconds."""
    return _cached_result.age_s


# ── Windows scanners ──────────────────────────────────────────────────────


def _no_window_kwargs() -> dict[str, Any]:
    """CREATE_NO_WINDOW for Windows subprocess calls."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _ps_query(command: str, timeout: int = 10) -> list[dict[str, Any]]:
    """Run a PowerShell command that returns JSON. Returns list of dicts."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            **_no_window_kwargs(),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout.strip())
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as exc:
        logger.debug("PowerShell query failed: %s", exc)
        return []


def _scan_monitors() -> list[dict[str, Any]]:
    """Enumerate monitors via screeninfo."""
    try:
        from screeninfo import get_monitors
    except ImportError:
        logger.debug("screeninfo not available, skipping monitor scan")
        return []

    result: list[dict[str, Any]] = []
    try:
        for i, m in enumerate(get_monitors()):
            is_primary = getattr(m, "is_primary", i == 0)
            result.append({
                "peripheral_id": f"monitor_{i}",
                "type": "monitor",
                "name": getattr(m, "name", f"Monitor {i}"),
                "manufacturer": "",
                "model": "",
                "device_id": getattr(m, "name", ""),
                "active": True,
                "is_default": bool(is_primary),
                "health": "ok",
                "properties": {
                    "width": m.width,
                    "height": m.height,
                    "x": m.x,
                    "y": m.y,
                    "is_primary": bool(is_primary),
                },
            })
    except Exception as exc:
        logger.debug("monitor scan failed: %s", exc)
    return result


def _scan_audio_devices() -> list[dict[str, Any]]:
    """Enumerate audio devices via WMI Win32_SoundDevice."""
    ps_cmd = (
        "Get-CimInstance Win32_SoundDevice | "
        "Select-Object Name, DeviceID, Manufacturer, Status, StatusInfo "
        "| ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, dev in enumerate(_ps_query(ps_cmd)):
        name = dev.get("Name", "").strip()
        if not name:
            continue
        name_lower = name.lower()
        if any(kw in name_lower for kw in ("microphone", "mic", "input", "recording")):
            ptype = "audio_input"
            pid = f"audio_in_{i}"
        else:
            ptype = "audio_output"
            pid = f"audio_out_{i}"
        status = dev.get("Status", "")
        devices.append({
            "peripheral_id": pid,
            "type": ptype,
            "name": name,
            "manufacturer": dev.get("Manufacturer", ""),
            "model": "",
            "device_id": dev.get("DeviceID", ""),
            "active": status == "OK",
            "is_default": False,
            "health": "ok" if status == "OK" else "degraded",
            "properties": {
                "status": status,
                "status_info": dev.get("StatusInfo"),
            },
        })
    return devices


def _scan_cameras() -> list[dict[str, Any]]:
    """Enumerate cameras via WMI Win32_PnPEntity."""
    ps_cmd = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'Camera' } | "
        "Select-Object Name, DeviceID, Manufacturer, Status "
        "| ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, entry in enumerate(_ps_query(ps_cmd, timeout=5)):
        name = entry.get("Name", "").strip()
        if not name:
            continue
        status = entry.get("Status", "")
        devices.append({
            "peripheral_id": f"camera_{i}",
            "type": "camera",
            "name": name,
            "manufacturer": entry.get("Manufacturer", ""),
            "model": "",
            "device_id": entry.get("DeviceID", ""),
            "active": status == "OK",
            "is_default": i == 0,
            "health": "ok" if status == "OK" else "degraded",
            "properties": {
                "physical_id": entry.get("DeviceID", ""),
            },
        })
    return devices


def _scan_input_devices() -> list[dict[str, Any]]:
    """Enumerate keyboards and mice via WMI."""
    devices: list[dict[str, Any]] = []
    queries = [
        ("keyboard", "Win32_Keyboard", "Name, DeviceID, Description, Status"),
        ("mouse", "Win32_PointingDevice", "Name, DeviceID, Description, Manufacturer, Status"),
    ]
    for device_class, wmi_class, fields in queries:
        ps_cmd = (
            f"Get-CimInstance {wmi_class} | "
            f"Select-Object {fields} | ConvertTo-Json -Compress"
        )
        for i, entry in enumerate(_ps_query(ps_cmd, timeout=5)):
            name = entry.get("Name", "").strip()
            if not name:
                continue
            dev_id = entry.get("DeviceID", "")
            connection = "usb"
            if "bluetooth" in dev_id.lower() or "bth" in dev_id.lower():
                connection = "bluetooth"
            elif "ps2" in dev_id.lower() or "acpi" in dev_id.lower():
                connection = "ps2"
            status = entry.get("Status", "")
            devices.append({
                "peripheral_id": f"input_{device_class}_{i}",
                "type": "input_device",
                "name": name,
                "manufacturer": entry.get("Manufacturer", ""),
                "model": entry.get("Description", ""),
                "device_id": dev_id,
                "active": status == "OK",
                "is_default": False,
                "health": "ok" if status == "OK" else "degraded",
                "properties": {
                    "device_class": device_class,
                    "connection": connection,
                },
            })
    return devices


def _scan_storage() -> list[dict[str, Any]]:
    """Enumerate logical disks and physical drive types."""
    ps_cmd = (
        "Get-CimInstance Win32_LogicalDisk | "
        "Where-Object { $_.DriveType -eq 3 } | "
        "Select-Object DeviceID, VolumeName, Size, FreeSpace, FileSystem "
        "| ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, disk in enumerate(_ps_query(ps_cmd)):
        drive_letter = disk.get("DeviceID", "")
        total = disk.get("Size") or 0
        free = disk.get("FreeSpace") or 0
        total_gb = round(total / (1024 ** 3), 1) if total else 0
        free_gb = round(free / (1024 ** 3), 1) if free else 0
        devices.append({
            "peripheral_id": f"storage_{i}",
            "type": "storage",
            "name": disk.get("VolumeName", "") or drive_letter,
            "manufacturer": "",
            "model": "",
            "device_id": drive_letter,
            "active": True,
            "is_default": drive_letter.upper().startswith("C"),
            "health": "ok",
            "properties": {
                "drive_letter": drive_letter,
                "total_gb": total_gb,
                "free_gb": free_gb,
                "fs_type": disk.get("FileSystem", ""),
            },
        })

    # Enrich with physical drive type (SSD/HDD/NVMe)
    phys_cmd = (
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object DeviceID, MediaType, Model, Size "
        "| ConvertTo-Json -Compress"
    )
    phys_drives = _ps_query(phys_cmd, timeout=5)
    for dev in devices:
        media_type = ""
        for phys in phys_drives:
            mt = (phys.get("MediaType") or "").lower()
            model = (phys.get("Model") or "").lower()
            if "ssd" in mt or "solid" in mt or "ssd" in model:
                media_type = "ssd"
            elif "nvme" in model:
                media_type = "nvme"
            elif "hdd" in mt or "hard" in mt:
                media_type = "hdd"
        if media_type:
            dev["properties"]["drive_type"] = media_type

    return devices


def _scan_network_interfaces() -> list[dict[str, Any]]:
    """Enumerate active network adapters."""
    ps_cmd = (
        "Get-CimInstance Win32_NetworkAdapter | "
        "Where-Object { $_.NetEnabled -eq $true } | "
        "Select-Object Name, DeviceID, MACAddress, Speed, Manufacturer, "
        "NetConnectionID | ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, nic in enumerate(_ps_query(ps_cmd)):
        name = nic.get("Name", "").strip()
        if not name:
            continue
        name_lower = name.lower()
        conn_id = (nic.get("NetConnectionID") or "").lower()
        if "tailscale" in name_lower or "tailscale" in conn_id:
            conn_type = "tailscale"
        elif "wi-fi" in conn_id or "wireless" in name_lower or "wifi" in name_lower:
            conn_type = "wifi"
        else:
            conn_type = "ethernet"
        speed = nic.get("Speed") or 0
        speed_mbps = round(int(speed) / 1_000_000) if speed else 0
        devices.append({
            "peripheral_id": f"net_{i}",
            "type": "network",
            "name": name,
            "manufacturer": nic.get("Manufacturer", ""),
            "model": "",
            "device_id": str(nic.get("DeviceID", "")),
            "active": True,
            "is_default": False,
            "health": "ok",
            "properties": {
                "mac": nic.get("MACAddress", ""),
                "speed_mbps": speed_mbps,
                "connection_type": conn_type,
                "connection_id": nic.get("NetConnectionID", ""),
            },
        })
    return devices


def _scan_display_adapters() -> list[dict[str, Any]]:
    """Enumerate GPU/display adapters via WMI."""
    ps_cmd = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name, DeviceID, AdapterRAM, DriverVersion, "
        "VideoProcessor, Status "
        "| ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, gpu in enumerate(_ps_query(ps_cmd)):
        name = gpu.get("Name", "").strip()
        if not name:
            continue
        adapter_ram = gpu.get("AdapterRAM") or 0
        vram_mb = round(int(adapter_ram) / (1024 ** 2)) if adapter_ram else 0
        status = gpu.get("Status", "")
        devices.append({
            "peripheral_id": f"display_adapter_{i}",
            "type": "display_adapter",
            "name": name,
            "manufacturer": "",
            "model": gpu.get("VideoProcessor", ""),
            "device_id": gpu.get("DeviceID", ""),
            "active": status == "OK",
            "is_default": i == 0,
            "health": "ok" if status == "OK" else "degraded",
            "properties": {
                "gpu_name": name,
                "vram_mb": vram_mb,
                "driver_version": gpu.get("DriverVersion", ""),
            },
        })
    return devices


def _scan_bluetooth() -> list[dict[str, Any]]:
    """Enumerate Bluetooth devices via WMI."""
    ps_cmd = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'Bluetooth' } | "
        "Select-Object Name, DeviceID, Manufacturer, Status "
        "| ConvertTo-Json -Compress"
    )
    devices: list[dict[str, Any]] = []
    for i, entry in enumerate(_ps_query(ps_cmd, timeout=5)):
        name = entry.get("Name", "").strip()
        if not name:
            continue
        status = entry.get("Status", "")
        devices.append({
            "peripheral_id": f"bt_{i}",
            "type": "bluetooth",
            "name": name,
            "manufacturer": entry.get("Manufacturer", ""),
            "model": "",
            "device_id": entry.get("DeviceID", ""),
            "active": status == "OK",
            "is_default": False,
            "health": "ok" if status == "OK" else "degraded",
            "properties": {},
        })
    return devices
