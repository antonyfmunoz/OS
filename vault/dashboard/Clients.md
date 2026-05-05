TABLE cohort, discipline_score, execution_blocks_weekly, habit_focus
FROM "08_Clients/Active"
WHERE type = "client"
SORT discipline_score ASC

at_risk: true

TABLE discipline_score, execution_blocks_weekly
FROM "08_Clients/Active"
WHERE type = "client" AND at_risk = true