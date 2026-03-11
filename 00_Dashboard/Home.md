TABLE status, pain_level, ownership_level, next_action, next_action_date
FROM "03_CRM"
WHERE type = "lead" AND status != "won" AND status != "lost"
SORT next_action_date ASC

TABLE offer, cohort, discipline_score, execution_blocks_weekly
FROM "08_Clients/Active"
WHERE type = "client"
SORT discipline_score DESC

not done
path includes 02_Daily
sort by due