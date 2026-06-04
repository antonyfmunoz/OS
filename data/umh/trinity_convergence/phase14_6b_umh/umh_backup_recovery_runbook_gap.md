# UMH Backup and Recovery Runbook Gap

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Current State: No Verified Backup/Recovery

### Neon Postgres

- Neon provides automatic point-in-time backups as a platform feature
- **No tested restore procedure** -- backup exists but has never been validated
- No documented runbook for restoring from Neon backup
- No known RTO (recovery time objective) or RPO (recovery point objective)

### JSONL Runtime Data

- Runtime state stored in `data/umh/organism/` as JSONL files (events, messages, reports, execution journal)
- **No backup mechanism** for JSONL data
- Files are on a single VPS disk with no replication
- Loss of VPS disk = loss of all runtime JSONL history

### Disaster Recovery

- **No disaster recovery plan** exists
- **Single VPS is a single point of failure** for all 4 Docker services
- Beast (Windows workstation) has a full repo mirror but is not configured for failover
- No automated failover or health-check-triggered recovery

## Risk Assessment

| Asset | Backup Exists | Backup Tested | Restore Documented |
|-------|--------------|---------------|-------------------|
| Neon Postgres | Yes (platform) | No | No |
| JSONL runtime data | No | N/A | No |
| Docker service configs | Yes (in repo) | N/A | Partial (compose.yml) |
| .env secrets | No offsite copy | N/A | No |
| Codebase | Yes (GitHub) | Yes | Yes |

## Recommended Actions

1. Test Neon restore from backup and document the procedure
2. Implement scheduled JSONL backup (to GitHub, S3, or Beast)
3. Document .env secrets in a secure vault with recovery procedure
4. Define RTO/RPO targets for each data class
5. Consider Beast as warm standby for critical services
