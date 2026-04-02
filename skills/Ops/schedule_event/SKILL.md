---
name: schedule-event
description: "Create a Google Calendar event from natural language input — triggered when the founder mentions scheduling, booking, setting up a call, meeting, or appointment."
allowed-tools: "Read, Bash"
version: 1.0
---

# Schedule Event

## Purpose
Create a Google Calendar event from natural language input.

## When to Use
When the founder mentions scheduling, booking, setting up a call, meeting, or appointment.

## Inputs
- title: event title
- start: natural language date/time ("next Tuesday at 2pm", "tomorrow at 10am")
- duration_minutes: optional, default 60
- attendee_email: optional
- description: optional context

## Process
1. Parse the natural language date/time to ISO format in PDT
2. Call create_calendar_event() with parsed params
3. Return confirmation with Meet link and event details

## Trust Level
EXECUTE — creates event immediately, confirms in Discord

## Outputs
- Event title, date/time, Meet link, attendee if set
