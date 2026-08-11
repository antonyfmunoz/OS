# DEFECTS — Curriculum Register (rehearsal run)

Rescue count: **0** — the Player One metric that gates Player Two.

## Outreach draft rejected on first pass
- **Book said:** Draft passes approval first time
- **Actually did:** Revised subject line, resubmitted
- **Why:** Deliberate D2 injection: rejection path must work
- **At:** 2026-08-10T22:44:37.397646+00:00

## First payment declined
- **Book said:** Payment succeeds at close
- **Actually did:** Rolled back to agreement-signed state, retried with new method
- **Why:** Deliberate D2 injection: decline/rollback path must work
- **At:** 2026-08-10T22:44:38.069354+00:00

## Unapproved send attempted
- **Book said:** No outbound without an approved record
- **Actually did:** Gate raised ApprovalRequired; send blocked
- **Why:** Deliberate D2 injection: the gate must block, and it did
- **At:** 2026-08-10T22:44:39.132385+00:00
