---
name: call-booking-confirmation
description: "Send a confirmation and reminder sequence after a call is booked to maximize show rate — run immediately when a Calendly or manual booking is confirmed."
allowed-tools: "Read, Bash"
version: 1.0
---

# Skill: Call Booking Confirmation

## Purpose
After a call is booked, send a confirmation and reminder sequence that maximizes show rate.

## Outcome
Prospect shows up prepared and committed. No-show rate minimized.

## Decision Criteria
- Call booked via Calendly or manual booking
- Run immediately after booking confirmed

## Execution Steps
1. Send confirmation within 5 minutes of booking:
   - Date and time (with timezone)
   - What to expect on the call
   - One sentence on what will be covered
2. Send reminder 24 hours before:
   - Reconfirm date and time
   - Create anticipation — this call has a purpose
   - Ask them to come with their biggest challenge in mind
3. Send reminder 1 hour before:
   - "See you in an hour" + Zoom/call link
4. If no confirmation reply received — flag to DEX

## Failure Modes
- Sending more than 3 messages total (creates friction, not anticipation)
- Generic confirmation with no specificity about what the call covers
- Missing the 1-hour reminder
- Sending reminders without the actual call link

## Measurement
- Show rate before and after implementation
- Reply rate to confirmation messages
