# Sales Dashboard

## Active Pipeline

```dataview
TABLE icp_score AS "Score", archetype AS "Archetype", kanban_stage AS "Stage", next_action AS "Next Action", next_action_date AS "Due"
FROM "03_CRM/Leads"
WHERE type = "lead" AND kanban_stage != "Won" AND kanban_stage != "Lost"
SORT next_action_date ASC
```

## Leads by Stage

```dataview
TABLE length(rows) AS "Count"
FROM "03_CRM/Leads"
WHERE type = "lead"
GROUP BY kanban_stage
```

## Active Clients

```dataview
TABLE offer, cohort, discipline_score, execution_blocks_weekly
FROM "08_Clients/Active"
WHERE type = "client"
SORT discipline_score DESC
```

## Open Tasks

```tasks
not done
path includes 02_Daily
sort by due
```
