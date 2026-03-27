Deploy changes to running services.

Arguments: $ARGUMENTS (service name, e.g. os-discord)

Steps:
1. Verify Python imports are clean for changed files
2. If Dockerfile unchanged: docker compose restart $ARGUMENTS
3. If Dockerfile changed: docker compose build --no-cache $ARGUMENTS && docker compose up -d $ARGUMENTS
4. Wait 15 seconds
5. Show last 10 log lines: docker logs $ARGUMENTS --tail 10
6. Report success or errors
