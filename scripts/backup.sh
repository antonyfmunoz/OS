#!/bin/bash
# EOS Daily Backup
# Backs up all critical local files to a dated archive.
# Runs daily at 6am via orchestrator.
set -euo pipefail

BACKUP_DIR="/opt/OS/backups"
DATE=$(date +%Y%m%d)
ARCHIVE="$BACKUP_DIR/eos_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
  /opt/OS/data/ \
  /opt/OS/12_Agents/ \
  /opt/OS/.claude/ \
  /opt/OS/eos_ai/*.py \
  /opt/OS/PHILOSOPHY.md \
  /opt/OS/PROTOCOLS.md \
  /opt/OS/CLAUDE.md \
  /opt/OS/ARCHITECTURE.md \
  2>/dev/null

echo "Backup created: $ARCHIVE"
echo "Size: $(du -sh "$ARCHIVE" | cut -f1)"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
echo "Old backups cleaned"
