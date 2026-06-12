import { useCallback, useEffect, useState } from 'react'
import { useRoomsStore } from '../stores/roomsStore'
import { ServerRail } from '../components/rooms/ServerRail'
import { ChannelSidebar } from '../components/rooms/ChannelSidebar'
import { RoomMainView } from '../components/rooms/RoomMainView'
import { RoomRightRail } from '../components/rooms/RoomRightRail'

const CH_SIDEBAR_KEY = 'rooms:chSidebarV2'
const RIGHT_RAIL_KEY = 'rooms:rightRailV2'

function loadBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key)
    if (v === null) return fallback
    return v === 'true'
  } catch { return fallback }
}

export function ConferenceRoomsPanel() {
  const fetchServers = useRoomsStore((s) => s.fetchServers)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const loading = useRoomsStore((s) => s.loading)
  const [channelSidebarCollapsed, setChannelSidebarCollapsed] = useState(() => loadBool(CH_SIDEBAR_KEY, true))
  const [rightRailCollapsed, setRightRailCollapsed] = useState(() => loadBool(RIGHT_RAIL_KEY, true))

  const toggleChannelSidebar = useCallback(() => setChannelSidebarCollapsed((v) => {
    const next = !v
    try { localStorage.setItem(CH_SIDEBAR_KEY, String(next)) } catch {}
    return next
  }), [])

  const toggleRightRail = useCallback(() => setRightRailCollapsed((v) => {
    const next = !v
    try { localStorage.setItem(RIGHT_RAIL_KEY, String(next)) } catch {}
    return next
  }), [])

  useEffect(() => {
    fetchServers()
  }, [fetchServers])

  return (
    <div className="flex h-full">
      <ServerRail />

      {activeServerId ? (
        <>
          <ChannelSidebar
            collapsed={channelSidebarCollapsed}
            onToggleCollapse={toggleChannelSidebar}
          />
          <div className="flex-1 flex flex-col min-w-0">
            <RoomMainView />
          </div>
          <RoomRightRail
            collapsed={rightRailCollapsed}
            onToggleCollapse={toggleRightRail}
          />
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          {loading ? (
            <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading servers...
            </p>
          ) : (
            <div className="text-center">
              <p className="text-sm font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                Conference Rooms
              </p>
              <p className="text-xs font-mono mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                Select or create a server to begin
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
