<<<<<<< Updated upstream
---
name: google_ads
description: "Use when querying Google Ads accounts via GAQL, drafting or mutating campaigns/ad groups/keywords/budgets, uploading offline or enhanced conversions, building Performance Max asset groups, running batch jobs, analyzing paid search performance for Initiate Arena lead gen or Lyfe Spectrum ecommerce, or wiring the google-ads-python SDK with developer token + OAuth refresh + login_customer_id."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://developers.google.com/google-ads/api/docs/start"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Google Ads API v23.1 (Feb 2026)"
sdk_version: "google-ads-python 26.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: Google Ads API

## What This Tool Does

The Google Ads API is the programmatic surface for everything you can do
in the Google Ads UI: create and mutate campaigns, ad groups, ads,
keywords, budgets, audiences, conversions, and assets; query reporting
metrics with GAQL (Google Ads Query Language); upload offline and enhanced
conversions back into Google Ads to close the loop on ROAS; and orchestrate
large changes via batch jobs. It is gRPC-first with a REST mirror,
version-pinned (`v23` is the URL segment), and accessed with a three-part
credential bundle: developer token, OAuth2 user credentials, and (for MCC
traversal) a login-customer-id header.

Core capabilities:

- **GAQL reporting** via `GoogleAdsService.Search` (paged) and
  `GoogleAdsService.SearchStream` (single streamed response — preferred for
  reports >10k rows)
- **Mutate operations** on every resource type, with `partial_failure` and
  `validate_only` modes for safe drafting
- **Bulk mutate** via `GoogleAdsService.Mutate` (cross-resource, atomic per
  resource group) and **BatchJobService** for million-operation jobs
- **Performance Max** campaign + asset group + asset linking in a single
  bulk mutate (required by the API)
- **Conversion uploads** — `ConversionUploadService.UploadClickConversions`
  for Enhanced Conversions for Leads, plus offline call/store conversions
- **Recommendations, change history, asset performance** — full surface
  parity with the Ads UI
- **Account management** — MCC traversal, account linking, user access

## EOS Integration

Google Ads is the paid acquisition substrate for two ventures:

- **Initiate Arena** — search + Performance Max for lead gen. Agents draft
  campaign structures, propose keyword expansions, surface negative-keyword
  candidates from search-term reports, and upload Enhanced Conversions for
  Leads from CRM closed-won events to teach Smart Bidding which leads
  actually pay.
- **Lyfe Spectrum** — Performance Max + Shopping for ecommerce. Agents
  analyze asset group performance, recommend creative rotations, and pull
  ROAS by product group nightly into Neon for the morning brief.

Authority model:
- Read-only GAQL queries — agent autonomous
- Drafts (`validate_only=True`) — agent autonomous
- Negative keyword adds, paused entities — agent + EA approval
- **Budget changes, bid changes, new campaigns going live, conversion
  uploads** — CRITICAL risk class, human-in-the-loop required (budget is
  real money). Agents prepare the diff, the founder confirms before
  `validate_only` flips off.

Canonical EOS pattern:
- Credentials in `eos_ai/.env` (never `google-ads.yaml` in repo)
- Single `GoogleAdsClient` cached per process, refreshed on auth error
- All reports go through `searchStream` not `search`
- Every mutate first runs with `validate_only=True` and the diff is logged
- Exponential backoff on `RESOURCE_EXHAUSTED`, honoring `retryDelay`

## Authentication

Three credentials, all required:

1. **Developer token** — issued by Google to your MCC. Tied to API access
   level (Test → Basic → Standard). Header: `developer-token`.
2. **OAuth2 user credentials** — `client_id`, `client_secret`,
   `refresh_token`. Generated via the Installed App flow against a Google
   account that has access to the target Google Ads accounts.
3. **login-customer-id** — the 10-digit MCC ID *without dashes*, sent as
   the `login-customer-id` header on every request that traverses an MCC.
   Required when the authenticated user accesses child accounts through a
   manager account.

EOS env vars (read by `GoogleAdsClient.load_from_env()`):

```
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=1//0...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
GOOGLE_ADS_USE_PROTO_PLUS=True
```

Access levels (matters for daily ops quota):
- **Test** — sandbox accounts only, no production calls
- **Basic** — 15,000 operations/day against production
- **Standard** — effectively unlimited for `Search`/`SearchStream`, subject
  to QPS rate limits

## Quick Reference

### Initialize the client

```python
import os, sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

from google.ads.googleads.client import GoogleAdsClient
client = GoogleAdsClient.load_from_env(version="v23")
```

### Run a GAQL report (streaming — preferred)

```python
ga_service = client.get_service("GoogleAdsService")
query = """
  SELECT
    campaign.id, campaign.name, campaign.status,
    metrics.cost_micros, metrics.conversions, metrics.clicks
  FROM campaign
  WHERE segments.date DURING LAST_7_DAYS
    AND campaign.status != 'REMOVED'
  ORDER BY metrics.cost_micros DESC
"""
stream = ga_service.search_stream(customer_id="1234567890", query=query)
for batch in stream:
    for row in batch.results:
        print(row.campaign.name, row.metrics.cost_micros / 1_000_000)
```

### Validate-only mutate (draft, no commit)

```python
campaign_service = client.get_service("CampaignService")
op = client.get_type("CampaignOperation")
campaign = op.update
campaign.resource_name = campaign_service.campaign_path("1234567890", "987")
campaign.status = client.enums.CampaignStatusEnum.PAUSED
client.copy_from(op.update_mask, {"paths": ["status"]})

response = campaign_service.mutate_campaigns(
    customer_id="1234567890",
    operations=[op],
    validate_only=True,        # DRY RUN — nothing committed
    partial_failure=False,
)
```

### Partial failure mutate

```python
response = campaign_service.mutate_campaigns(
    customer_id="1234567890",
    operations=ops,
    partial_failure=True,
)
if response.partial_failure_error.code != 0:
    failure = client.get_type("GoogleAdsFailure")
    failure_bytes = response.partial_failure_error.details[0].value
    failure.ParseFromString(failure_bytes)
    for err in failure.errors:
        print("op", err.location.field_path_elements[0].index, err.message)
```

### Upload Enhanced Conversion for Leads

```python
import hashlib
def norm_hash(s): return hashlib.sha256(s.strip().lower().encode()).hexdigest()

upload_svc = client.get_service("ConversionUploadService")
click = client.get_type("ClickConversion")
click.conversion_action = client.get_service("ConversionActionService") \
    .conversion_action_path("1234567890", CONVERSION_ACTION_ID)
click.conversion_date_time = "2026-04-06 14:00:00+00:00"
click.conversion_value = 750.0
click.currency_code = "USD"

uid = client.get_type("UserIdentifier")
uid.hashed_email = norm_hash("lead@example.com")
click.user_identifiers.append(uid)

resp = upload_svc.upload_click_conversions(
    customer_id="1234567890",
    conversions=[click],
    partial_failure=True,
)
```

## Conceptual Model

**Resource graph + version-pinned RPC.** Every entity in Google Ads is a
resource with a stable `resource_name` of the form
`customers/{cid}/{type}/{id}`. Every mutation is an operation on a typed
service (`CampaignService`, `AdGroupService`, ...) and every read is a
GAQL query against the unified `GoogleAdsService.Search(Stream)` endpoint.
The API is version-pinned in the URL (`v23`), and Google deprecates roughly
every 8 months — pin in code, upgrade deliberately.

**Three things move through every request:** the `developer-token` header
(who is the app), OAuth bearer (who is the user), and `login-customer-id`
header (which MCC the user is acting through). Get any of those wrong and
you get `PERMISSION_DENIED` with a near-useless message.

**Quota is operations/day, not requests/day.** A `searchStream` call is
one operation regardless of how many rows stream back. A bulk mutate with
500 operations counts as 500. Standard access removes the daily cap on
`Search`/`SearchStream` but the per-CID QPS rate limit (token bucket)
always applies.

## Gotchas

- **Forgetting `login-customer-id`** when accessing child accounts via an
  MCC → `USER_PERMISSION_DENIED`. Set the header on every call.
- **Customer IDs with dashes** (`123-456-7890`) → invalid. Strip dashes
  always: `cid.replace("-", "")`.
- **Money is micros.** `cost_micros = 1_500_000` means $1.50. Forgetting
  to divide by 1,000,000 misreports spend by 6 orders of magnitude.
- **Reusing a `GoogleAdsClient` across forks** → broken gRPC channel state.
  Initialize the client *after* the fork.
- **`use_proto_plus=False`** changes the message type from proto-plus to
  raw protobuf and breaks every `client.copy_from` and dot-attribute call
  in EOS code. Always `True`.
- **Version pinning drift.** v17 and v18 are dead (April 2026). The current
  active version is **v23** (released Feb 2026 as v23.1). Pin
  `version="v23"` explicitly in `load_from_env`.
- **`validate_only=True` does NOT skip quota.** Drafts still count.
- **Performance Max requires atomic creation.** AssetGroup + minimum
  required AssetGroupAssets must be in the *same* `googleads_service.mutate`
  call. Splitting them fails validation.
- **Enhanced Conversions hashing must be normalized first** (lowercase,
  trim, strip phone formatting to E.164) *before* SHA-256. Hashing raw
  input silently produces 0% match rate.
- **GAQL `LIMIT` is supported but `OFFSET` is not.** Pagination is via
  `page_token`, not offset.
- **`partial_failure_error.details[0].value` is bytes** that you must
  `ParseFromString` into a `GoogleAdsFailure`. Treating it as a string
  prints garbage.
- **`RESOURCE_EXHAUSTED`** has a `retryDelay` field — honor it instead of
  hardcoded sleeps. Exponential backoff with jitter on top.
- **Test accounts cannot serve ads** and cannot upload conversions to
  production conversion actions. Don't try to validate Enhanced Conversions
  in a test MCC.
- **BatchJobService caps**: 1M operations per job, 100 active+pending jobs
  per account. Polling `batch_job.status` is the only completion signal.
- **Budgets are shared resources** — mutating a `CampaignBudget` affects
  every campaign linked to it. Always read campaign linkage first.
- **CRITICAL EOS rule:** any mutate that changes spend (budget amount, bid
  strategy target, campaign status going to ENABLED) requires human
  approval. Agents draft with `validate_only=True`, log the diff, and stop.

See references/best_practices.md for the full 19-section creator-level knowledge base.
=======
---
name: google_ads
description: "Use when querying Google Ads accounts via GAQL, drafting or mutating campaigns/ad groups/keywords/budgets, uploading offline or enhanced conversions, building Performance Max asset groups, running batch jobs, analyzing paid search performance for Initiate Arena lead gen or Lyfe Spectrum ecommerce, or wiring the google-ads-python SDK with developer token + OAuth refresh + login_customer_id."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://developers.google.com/google-ads/api/docs/start"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Google Ads API v23.1 (Feb 2026)"
sdk_version: "google-ads-python 26.x"
speed_category: stable
---

# Tool: Google Ads API

## What This Tool Does

The Google Ads API is the programmatic surface for everything you can do
in the Google Ads UI: create and mutate campaigns, ad groups, ads,
keywords, budgets, audiences, conversions, and assets; query reporting
metrics with GAQL (Google Ads Query Language); upload offline and enhanced
conversions back into Google Ads to close the loop on ROAS; and orchestrate
large changes via batch jobs. It is gRPC-first with a REST mirror,
version-pinned (`v23` is the URL segment), and accessed with a three-part
credential bundle: developer token, OAuth2 user credentials, and (for MCC
traversal) a login-customer-id header.

Core capabilities:

- **GAQL reporting** via `GoogleAdsService.Search` (paged) and
  `GoogleAdsService.SearchStream` (single streamed response — preferred for
  reports >10k rows)
- **Mutate operations** on every resource type, with `partial_failure` and
  `validate_only` modes for safe drafting
- **Bulk mutate** via `GoogleAdsService.Mutate` (cross-resource, atomic per
  resource group) and **BatchJobService** for million-operation jobs
- **Performance Max** campaign + asset group + asset linking in a single
  bulk mutate (required by the API)
- **Conversion uploads** — `ConversionUploadService.UploadClickConversions`
  for Enhanced Conversions for Leads, plus offline call/store conversions
- **Recommendations, change history, asset performance** — full surface
  parity with the Ads UI
- **Account management** — MCC traversal, account linking, user access

## EOS Integration

Google Ads is the paid acquisition substrate for two ventures:

- **Initiate Arena** — search + Performance Max for lead gen. Agents draft
  campaign structures, propose keyword expansions, surface negative-keyword
  candidates from search-term reports, and upload Enhanced Conversions for
  Leads from CRM closed-won events to teach Smart Bidding which leads
  actually pay.
- **Lyfe Spectrum** — Performance Max + Shopping for ecommerce. Agents
  analyze asset group performance, recommend creative rotations, and pull
  ROAS by product group nightly into Neon for the morning brief.

Authority model:
- Read-only GAQL queries — agent autonomous
- Drafts (`validate_only=True`) — agent autonomous
- Negative keyword adds, paused entities — agent + EA approval
- **Budget changes, bid changes, new campaigns going live, conversion
  uploads** — CRITICAL risk class, human-in-the-loop required (budget is
  real money). Agents prepare the diff, the founder confirms before
  `validate_only` flips off.

Canonical EOS pattern:
- Credentials in `eos_ai/.env` (never `google-ads.yaml` in repo)
- Single `GoogleAdsClient` cached per process, refreshed on auth error
- All reports go through `searchStream` not `search`
- Every mutate first runs with `validate_only=True` and the diff is logged
- Exponential backoff on `RESOURCE_EXHAUSTED`, honoring `retryDelay`

## Authentication

Three credentials, all required:

1. **Developer token** — issued by Google to your MCC. Tied to API access
   level (Test → Basic → Standard). Header: `developer-token`.
2. **OAuth2 user credentials** — `client_id`, `client_secret`,
   `refresh_token`. Generated via the Installed App flow against a Google
   account that has access to the target Google Ads accounts.
3. **login-customer-id** — the 10-digit MCC ID *without dashes*, sent as
   the `login-customer-id` header on every request that traverses an MCC.
   Required when the authenticated user accesses child accounts through a
   manager account.

EOS env vars (read by `GoogleAdsClient.load_from_env()`):

```
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=1//0...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
GOOGLE_ADS_USE_PROTO_PLUS=True
```

Access levels (matters for daily ops quota):
- **Test** — sandbox accounts only, no production calls
- **Basic** — 15,000 operations/day against production
- **Standard** — effectively unlimited for `Search`/`SearchStream`, subject
  to QPS rate limits

## Quick Reference

### Initialize the client

```python
import os, sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

from google.ads.googleads.client import GoogleAdsClient
client = GoogleAdsClient.load_from_env(version="v23")
```

### Run a GAQL report (streaming — preferred)

```python
ga_service = client.get_service("GoogleAdsService")
query = """
  SELECT
    campaign.id, campaign.name, campaign.status,
    metrics.cost_micros, metrics.conversions, metrics.clicks
  FROM campaign
  WHERE segments.date DURING LAST_7_DAYS
    AND campaign.status != 'REMOVED'
  ORDER BY metrics.cost_micros DESC
"""
stream = ga_service.search_stream(customer_id="1234567890", query=query)
for batch in stream:
    for row in batch.results:
        print(row.campaign.name, row.metrics.cost_micros / 1_000_000)
```

### Validate-only mutate (draft, no commit)

```python
campaign_service = client.get_service("CampaignService")
op = client.get_type("CampaignOperation")
campaign = op.update
campaign.resource_name = campaign_service.campaign_path("1234567890", "987")
campaign.status = client.enums.CampaignStatusEnum.PAUSED
client.copy_from(op.update_mask, {"paths": ["status"]})

response = campaign_service.mutate_campaigns(
    customer_id="1234567890",
    operations=[op],
    validate_only=True,        # DRY RUN — nothing committed
    partial_failure=False,
)
```

### Partial failure mutate

```python
response = campaign_service.mutate_campaigns(
    customer_id="1234567890",
    operations=ops,
    partial_failure=True,
)
if response.partial_failure_error.code != 0:
    failure = client.get_type("GoogleAdsFailure")
    failure_bytes = response.partial_failure_error.details[0].value
    failure.ParseFromString(failure_bytes)
    for err in failure.errors:
        print("op", err.location.field_path_elements[0].index, err.message)
```

### Upload Enhanced Conversion for Leads

```python
import hashlib
def norm_hash(s): return hashlib.sha256(s.strip().lower().encode()).hexdigest()

upload_svc = client.get_service("ConversionUploadService")
click = client.get_type("ClickConversion")
click.conversion_action = client.get_service("ConversionActionService") \
    .conversion_action_path("1234567890", CONVERSION_ACTION_ID)
click.conversion_date_time = "2026-04-06 14:00:00+00:00"
click.conversion_value = 750.0
click.currency_code = "USD"

uid = client.get_type("UserIdentifier")
uid.hashed_email = norm_hash("lead@example.com")
click.user_identifiers.append(uid)

resp = upload_svc.upload_click_conversions(
    customer_id="1234567890",
    conversions=[click],
    partial_failure=True,
)
```

## Conceptual Model

**Resource graph + version-pinned RPC.** Every entity in Google Ads is a
resource with a stable `resource_name` of the form
`customers/{cid}/{type}/{id}`. Every mutation is an operation on a typed
service (`CampaignService`, `AdGroupService`, ...) and every read is a
GAQL query against the unified `GoogleAdsService.Search(Stream)` endpoint.
The API is version-pinned in the URL (`v23`), and Google deprecates roughly
every 8 months — pin in code, upgrade deliberately.

**Three things move through every request:** the `developer-token` header
(who is the app), OAuth bearer (who is the user), and `login-customer-id`
header (which MCC the user is acting through). Get any of those wrong and
you get `PERMISSION_DENIED` with a near-useless message.

**Quota is operations/day, not requests/day.** A `searchStream` call is
one operation regardless of how many rows stream back. A bulk mutate with
500 operations counts as 500. Standard access removes the daily cap on
`Search`/`SearchStream` but the per-CID QPS rate limit (token bucket)
always applies.

## Gotchas

- **Forgetting `login-customer-id`** when accessing child accounts via an
  MCC → `USER_PERMISSION_DENIED`. Set the header on every call.
- **Customer IDs with dashes** (`123-456-7890`) → invalid. Strip dashes
  always: `cid.replace("-", "")`.
- **Money is micros.** `cost_micros = 1_500_000` means $1.50. Forgetting
  to divide by 1,000,000 misreports spend by 6 orders of magnitude.
- **Reusing a `GoogleAdsClient` across forks** → broken gRPC channel state.
  Initialize the client *after* the fork.
- **`use_proto_plus=False`** changes the message type from proto-plus to
  raw protobuf and breaks every `client.copy_from` and dot-attribute call
  in EOS code. Always `True`.
- **Version pinning drift.** v17 and v18 are dead (April 2026). The current
  active version is **v23** (released Feb 2026 as v23.1). Pin
  `version="v23"` explicitly in `load_from_env`.
- **`validate_only=True` does NOT skip quota.** Drafts still count.
- **Performance Max requires atomic creation.** AssetGroup + minimum
  required AssetGroupAssets must be in the *same* `googleads_service.mutate`
  call. Splitting them fails validation.
- **Enhanced Conversions hashing must be normalized first** (lowercase,
  trim, strip phone formatting to E.164) *before* SHA-256. Hashing raw
  input silently produces 0% match rate.
- **GAQL `LIMIT` is supported but `OFFSET` is not.** Pagination is via
  `page_token`, not offset.
- **`partial_failure_error.details[0].value` is bytes** that you must
  `ParseFromString` into a `GoogleAdsFailure`. Treating it as a string
  prints garbage.
- **`RESOURCE_EXHAUSTED`** has a `retryDelay` field — honor it instead of
  hardcoded sleeps. Exponential backoff with jitter on top.
- **Test accounts cannot serve ads** and cannot upload conversions to
  production conversion actions. Don't try to validate Enhanced Conversions
  in a test MCC.
- **BatchJobService caps**: 1M operations per job, 100 active+pending jobs
  per account. Polling `batch_job.status` is the only completion signal.
- **Budgets are shared resources** — mutating a `CampaignBudget` affects
  every campaign linked to it. Always read campaign linkage first.
- **CRITICAL EOS rule:** any mutate that changes spend (budget amount, bid
  strategy target, campaign status going to ENABLED) requires human
  approval. Agents draft with `validate_only=True`, log the diff, and stop.

See references/best_practices.md for the full 19-section creator-level knowledge base.
>>>>>>> Stashed changes
