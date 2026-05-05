---
type: codebase-file
path: eos_ai/travel_manager.py
module: eos_ai.travel_manager
lines: 359
size: 10089
generated: 2026-04-12
---

# eos_ai/travel_manager.py

Travel Manager — full trip logistics management.
When a trip is detected, DEX builds a complete
travel brief and manages logistics.

**Lines:** 359 | **Size:** 10,089 bytes

## Contains

- **fn** [[eos_ai-travel_manager-py-detect_travel_event]]`(event) → bool`
- **fn** [[eos_ai-travel_manager-py-build_travel_brief]]`(event_title, destination, start_date, end_date, attendees, ctx) → str`
- **fn** [[eos_ai-travel_manager-py-log_trip]]`(title, destination, start_date, end_date, ctx) → bool`
- **fn** [[eos_ai-travel_manager-py-research_flights]]`(origin, destination, date, return_date) → str`
- **fn** [[eos_ai-travel_manager-py-research_hotels]]`(city, check_in, check_out, budget_per_night, preferences) → str`
- **fn** [[eos_ai-travel_manager-py-research_restaurants]]`(city, occasion, budget, dietary) → str`
- **fn** [[eos_ai-travel_manager-py-generate_trip_itinerary]]`(trip_name, destination, start_date, end_date, meetings, hotel, ctx) → str`
- **fn** [[eos_ai-travel_manager-py-log_loyalty_program]]`(program, provider, account_number, points_balance, tier, ctx) → bool`
- **fn** [[eos_ai-travel_manager-py-reconcile_trip_expenses]]`(trip_name, expenses, ctx) → dict`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
