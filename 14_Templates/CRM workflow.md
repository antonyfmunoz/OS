---
type: workflow
department: sales
status: active
owner: Antony
trigger: new lead
outcome: create new lead in CRM
tags:
  - workflow
  - ai
  - crm
---
# Workflow

## Purpose
## Trigger
## Inputs
## Steps
1.
2.
3.

## Output
## Failure Points
## Improvements


Here’s the exact way to run CRM.

## New lead comes in

Create a lead note using the Lead Template.

Put it in:  
`03_CRM/Leads`

## If qualified

Move it to:  
`03_CRM/Qualified`

Change:

status: qualified

## If call booked

Move to:  
`03_CRM/Booked`

Set:

status: booked  
next_action: sales_call

## If won

Move to:  
`03_CRM/Won`

Set:

status: won

Then create a corresponding client note in:  
`08_Clients/Active`

## If lost

Move to:  
`03_CRM/Lost`

Set:

status: lost  
loss_reason:

This gives you a file-based CRM that still behaves like a database.