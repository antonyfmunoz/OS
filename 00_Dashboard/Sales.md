TABLE platform, source, pain_level, next_action
FROM "03_CRM/Leads"
WHERE type = "lead"
SORT file.ctime DESC

TABLE pain_level, ownership_level, next_action_date
FROM "03_CRM/Qualified"
WHERE type = "lead"
SORT next_action_date ASC

# Lost Reason:

TABLE loss_reason, pain_level, ownership_level
FROM "03_CRM/Lost"
WHERE type = "lead"
SORT file.mtime DESC