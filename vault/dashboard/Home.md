# Home Dashboard

## New Leads

```dataview
TABLE icp_score AS "Score", archetype AS "Archetype", source AS "Source", next_action AS "Next Action"
FROM "03_CRM/Leads"
WHERE type = "lead" AND kanban_stage = "New"
SORT file.ctime DESC
```

## Full Pipeline

```dataview
TABLE icp_score AS "Score", archetype AS "Archetype", kanban_stage AS "Stage", next_action_date AS "Due"
FROM "03_CRM/Leads"
WHERE type = "lead" AND kanban_stage != "Won" AND kanban_stage != "Lost"
SORT next_action_date ASC
```

## Lost Leads

```dataview
TABLE icp_score AS "Score", archetype AS "Archetype", source AS "Source"
FROM "03_CRM/Leads"
WHERE type = "lead" AND kanban_stage = "Lost"
SORT file.mtime DESC
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
