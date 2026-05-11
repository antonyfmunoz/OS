#!/bin/bash
# EOS Daily Backup
# Backs up all critical local files to a dated archive.
# Runs daily at 6am via orchestrator.
set -euo pipefail

BACKUP_DIR="${UMH_ROOT:-/opt/OS}/backups"
DATE=$(date +%Y%m%d)
ARCHIVE="$BACKUP_DIR/eos_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
  ${UMH_ROOT:-/opt/OS}/data/ \
  ${UMH_ROOT:-/opt/OS}/12_Agents/ \
  ${UMH_ROOT:-/opt/OS}/.claude/ \
  ${UMH_ROOT:-/opt/OS}/runtime/*.py \
  ${UMH_ROOT:-/opt/OS}/PHILOSOPHY.md \
  ${UMH_ROOT:-/opt/OS}/PROTOCOLS.md \
  ${UMH_ROOT:-/opt/OS}/CLAUDE.md \
  ${UMH_ROOT:-/opt/OS}/ARCHITECTURE.md \
  2>/dev/null

echo "Backup created: $ARCHIVE"
echo "Size: $(du -sh "$ARCHIVE" | cut -f1)"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
echo "Old backups cleaned"
