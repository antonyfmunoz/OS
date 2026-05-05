# AWS — Creator-Level Best Practices (Operator's-Eye View)

Last researched: 2026-04-06.
Scope: AWS CLI v2 2.17.x, boto3 1.35.x, IAM Identity Center, S3, EC2, Lambda,
CloudWatch, billing, STS, SSM Parameter Store. Per-service deep dives are
out of scope and deferred to future skill waves. This document treats AWS as
ONE tool from the perspective of an operator running a small production
footprint alongside a Tailscale-private VPS.

---

## Authentication

AWS authentication is the credential chain. boto3, botocore, and the AWS CLI
v2 share an identical resolution order. If you understand the chain you can
debug 90% of "why doesn't my call work" problems in under a minute.

**Resolution order (first hit wins):**

1. Constructor / CLI flag overrides
   - `boto3.client("s3", aws_access_key_id=..., aws_secret_access_key=..., aws_session_token=...)`
   - `aws --profile X --region Y ...`
2. Environment variables
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN` (required for any temporary creds)
   - `AWS_PROFILE`
   - `AWS_REGION` (newer) / `AWS_DEFAULT_REGION` (older — both honored)
   - `AWS_DEFAULT_OUTPUT`
3. Assume-role with web identity (`AWS_WEB_IDENTITY_TOKEN_FILE` + `AWS_ROLE_ARN`) — used by EKS IRSA, GitHub Actions OIDC
4. SSO cache — `~/.aws/sso/cache/<sha1>.json` referenced from a `[profile X]` block with `sso_session = ...`
5. Shared credentials file — `~/.aws/credentials` (`AWS_SHARED_CREDENTIALS_FILE`)
6. Shared config file — `~/.aws/config` (`AWS_CONFIG_FILE`)
7. ECS / App Runner container credentials — `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` or `AWS_CONTAINER_CREDENTIALS_FULL_URI`
8. EC2 Instance Metadata Service v2 (IMDSv2) — `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>`

**The four credential types:**

1. **Long-lived IAM user access keys** (`AKIA...`). Avoid. The 2017–2024
   era of AWS security incidents is overwhelmingly leaked AKIA keys.
2. **STS temporary credentials** (`ASIA...` + session token). Issued by
   AssumeRole, AssumeRoleWithSAML, AssumeRoleWithWebIdentity, GetSessionToken.
   1–12 hour lifetime. Default for SSO and instance roles under the hood.
3. **IAM Identity Center (SSO) tokens.** A bearer token cached locally; the
   CLI/SDK exchanges it for STS creds per call. 12-hour default access token,
   refreshable up to 90 days with `sso_registration_scopes`.
4. **Instance / container role credentials.** STS creds delivered via metadata
   service. Auto-rotated by AWS. Code never sees the keys, just calls boto3.

**`~/.aws/config` — modern SSO profile:**

```ini
[sso-session eos]
sso_start_url = https://d-9067abcdef.awsapps.com/start
sso_region = us-west-2
sso_registration_scopes = sso:account:access

[profile eos-admin]
sso_session = eos
sso_account_id = 123456789012
sso_role_name = AdministratorAccess
region = us-west-2
output = json

[profile eos-deploy]
sso_session = eos
sso_account_id = 123456789012
sso_role_name = EOSDeployRole
region = us-west-2
output = json
```

**Profile chaining (AssumeRole from a base profile):**

```ini
[profile eos-base]
sso_session = eos
sso_account_id = 111111111111
sso_role_name = ReadOnly
region = us-west-2

[profile eos-prod-deploy]
role_arn = arn:aws:iam::222222222222:role/eos-deploy
source_profile = eos-base
region = us-west-2
duration_seconds = 3600
```

**Verification one-liner:**

```bash
aws sts get-caller-identity
# {
#   "UserId": "AIDA...",  or "AROA...:session-name" for assumed role
#   "Account": "123456789012",
#   "Arn": "arn:aws:sts::123456789012:assumed-role/AdministratorAccess/afm@munoz.co"
# }
```

If `Arn` starts with `arn:aws:iam::...:user/...` you are on long-lived keys.
If `arn:aws:sts::...:assumed-role/...` you are on temporary creds. Prefer the latter.

---

## Core Operations with Exact Signatures

### S3 — boto3

```python
import boto3
s3 = boto3.client("s3", region_name="us-west-2")

# Upload (handles multipart automatically over 8 MB)
s3.upload_file(
    Filename="local.bin",
    Bucket="eos-media-prod",
    Key="2026/04/local.bin",
    ExtraArgs={"ServerSideEncryption": "AES256", "ContentType": "application/octet-stream"},
)

# Download
s3.download_file("eos-media-prod", "2026/04/local.bin", "local.bin")

# Stream a small object into memory
obj = s3.get_object(Bucket="eos-media-prod", Key="2026/04/local.bin")
body_bytes = obj["Body"].read()

# Presigned URL
url = s3.generate_presigned_url(
    ClientMethod="get_object",
    Params={"Bucket": "eos-media-prod", "Key": "2026/04/local.bin"},
    ExpiresIn=3600,                 # max 7 days for sigv4
    HttpMethod="GET",
)

# Presigned POST (browser uploads)
post = s3.generate_presigned_post(
    Bucket="eos-media-prod",
    Key="uploads/${filename}",
    Conditions=[["content-length-range", 0, 10_485_760]],
    ExpiresIn=900,
)
```

### EC2 — boto3

```python
ec2 = boto3.client("ec2", region_name="us-west-2")
resp = ec2.run_instances(
    ImageId="ami-0abcdef1234567890",   # Amazon Linux 2023 in us-west-2
    InstanceType="t4g.small",
    KeyName="afm-laptop",
    MinCount=1, MaxCount=1,
    SecurityGroupIds=["sg-0abc"],
    SubnetId="subnet-0abc",
    MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
    BlockDeviceMappings=[{
        "DeviceName": "/dev/xvda",
        "Ebs": {"VolumeSize": 20, "VolumeType": "gp3", "DeleteOnTermination": True},
    }],
    TagSpecifications=[{"ResourceType": "instance",
        "Tags": [{"Key": "Project", "Value": "eos"}, {"Key": "Env", "Value": "dev"}]}],
)
```

### Lambda — boto3

```python
lam = boto3.client("lambda", region_name="us-west-2")
with open("function.zip", "rb") as f:
    lam.create_function(
        FunctionName="eos-webhook",
        Runtime="python3.12",
        Role="arn:aws:iam::123456789012:role/eos-lambda-exec",
        Handler="handler.lambda_handler",
        Code={"ZipFile": f.read()},
        Timeout=15, MemorySize=256,
        Environment={"Variables": {"NEON_URL": "..."}},
        Architectures=["arm64"],     # cheaper, usually faster on Graviton
        TracingConfig={"Mode": "Active"},
    )

resp = lam.invoke(
    FunctionName="eos-webhook",
    InvocationType="RequestResponse",  # or "Event" for fire-and-forget
    Payload=b'{"hello":"world"}',
)
print(resp["Payload"].read())
```

### CloudWatch Logs — boto3

```python
logs = boto3.client("logs", region_name="us-west-2")
logs.put_retention_policy(logGroupName="/aws/lambda/eos-webhook", retentionInDays=14)

# Insights query
q = logs.start_query(
    logGroupName="/aws/lambda/eos-webhook",
    startTime=int(time.time()) - 3600,
    endTime=int(time.time()),
    queryString="fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50",
)
while True:
    r = logs.get_query_results(queryId=q["queryId"])
    if r["status"] in ("Complete", "Failed", "Cancelled"):
        break
    time.sleep(1)
```

### STS — boto3

```python
sts = boto3.client("sts")
creds = sts.assume_role(
    RoleArn="arn:aws:iam::222222222222:role/eos-deploy",
    RoleSessionName="afm-script",
    DurationSeconds=3600,
)["Credentials"]

assumed = boto3.Session(
    aws_access_key_id=creds["AccessKeyId"],
    aws_secret_access_key=creds["SecretAccessKey"],
    aws_session_token=creds["SessionToken"],
    region_name="us-west-2",
)
```

### SSM Parameter Store — boto3

```python
ssm = boto3.client("ssm", region_name="us-west-2")
ssm.put_parameter(Name="/eos/prod/openai_key", Value="sk-...", Type="SecureString", Overwrite=True)
val = ssm.get_parameter(Name="/eos/prod/openai_key", WithDecryption=True)["Parameter"]["Value"]

# Bulk read by path
page = ssm.get_paginator("get_parameters_by_path")
for p in page.paginate(Path="/eos/prod/", Recursive=True, WithDecryption=True):
    for param in p["Parameters"]:
        print(param["Name"], "=", param["Value"])
```

---

## Pagination Patterns

Almost every list-* call is paginated. Never trust a single response.

```python
# WRONG — silently truncates at 1000 keys
resp = s3.list_objects_v2(Bucket="eos-media-prod")
for obj in resp["Contents"]:
    ...

# RIGHT — paginator handles NextContinuationToken
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket="eos-media-prod", Prefix="2026/04/"):
    for obj in page.get("Contents", []):
        print(obj["Key"], obj["Size"])
```

CLI equivalent: `--no-paginate` to disable, `--page-size N` to control,
`--max-items N` to cap. By default the CLI auto-paginates to completion.

JMESPath inside the CLI: `--query 'Reservations[].Instances[].InstanceId'`
runs after pagination, not before, so don't use it as a server-side filter.

---

## Rate Limits

- **S3**: 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD per prefix per second.
  Hot prefix → use random key prefixes or the new automatic prefix scaling.
- **EC2 RunInstances**: account-level instance limits + API throttling.
- **Lambda**: 1,000 concurrent executions account-default; raise via support.
  Burst limit 500–3000 depending on region.
- **CloudWatch Logs PutLogEvents**: 5 requests/sec per log stream.
- **STS**: very high (thousands/sec) but throttled per account.
- **API Gateway / Lambda Function URL**: configurable per-route throttling.

All AWS APIs return `ThrottlingException` / `RequestLimitExceeded` /
`ProvisionedThroughputExceededException`. boto3 retries automatically with
exponential backoff. Tune via:

```python
from botocore.config import Config
cfg = Config(retries={"max_attempts": 10, "mode": "adaptive"}, connect_timeout=5, read_timeout=30)
boto3.client("s3", config=cfg)
```

---

## Error Codes and Recovery

- **`AccessDenied` / `UnauthorizedOperation`** → IAM. Run
  `aws sts get-caller-identity` first, then check the policy attached to that
  principal AND any resource policy on the target. Use the IAM Policy
  Simulator. CloudTrail will record the denied call with the exact missing
  action.
- **`NoSuchBucket` / `NoSuchKey`** → wrong region (bucket region != client
  region returns this for some path styles), wrong account, or actually missing.
- **`InvalidClientTokenId`** → stale or wrong access key. Re-`aws sso login`.
- **`ExpiredToken`** → STS creds aged out. Re-assume or re-SSO-login.
- **`SignatureDoesNotMatch`** → clock drift > 5 minutes (NTP), or you signed
  for the wrong region/service.
- **`ThrottlingException`** → backoff. Don't catch and retry instantly.
- **`RequestTimeTooSkewed`** → fix system clock. `timedatectl` on Linux.
- **`OptInRequired`** → region not enabled in this account. Some regions
  (af-south-1, me-central-1, etc.) require explicit opt-in.
- **`InsufficientInstanceCapacity`** → AWS literally has no boxes of that
  type in that AZ right now. Try another AZ or instance type.
- **`MalformedPolicyDocument`** → JSON valid but IAM grammar wrong. Use the
  visual editor first time, then copy.

CLI debugging trick: `aws s3 ls --debug 2>&1 | less` shows the full signed
request, headers, response body. Indispensable for "why is this denied."

---

## SDK Idioms

### Session vs client vs resource

- **Session** (`boto3.Session`) — credential + region holder. Cheap to
  create. Pass `profile_name=` here, not on the client.
- **Client** (`session.client("s3")`) — low-level, 1:1 with AWS API. The
  default. Use this.
- **Resource** (`session.resource("s3")`) — higher-level OO wrapper.
  **Deprecated** as of boto3 1.34 — no new services added, existing ones
  frozen. Migrate off.

### Always pin region

```python
# WRONG — picks up shell, then profile, then who-knows-what
boto3.client("s3")

# RIGHT
boto3.client("s3", region_name="us-west-2")
```

### Reuse clients

Clients are thread-safe and expensive to create (TLS, signing setup).
Module-level singletons or `lru_cache` them per (service, region).

### Use waiters

```python
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=["i-0abc"], WaiterConfig={"Delay": 5, "MaxAttempts": 60})
```

### Stream large S3 objects

```python
obj = s3.get_object(Bucket="b", Key="k")
for chunk in obj["Body"].iter_chunks(chunk_size=64 * 1024):
    sink.write(chunk)
```

### Don't serialize clients across processes

botocore clients hold open sockets and signing state, and aren't safe to
serialize/deserialize across process boundaries. Recreate per process.

---

## Anti-Patterns

- **Long-lived IAM user keys in `.env`.** The reason every credential leak
  hits the news. Use SSO or instance roles.
- **Wildcard IAM policies** (`Action: "*", Resource: "*"`). Even temporarily.
  Even "just for now." Even on dev.
- **Public S3 buckets for "convenience."** Use presigned URLs or CloudFront
  with OAC. The default block-public-access is on for a reason.
- **Logging credentials.** boto3 debug mode prints headers including
  `Authorization`. Never paste full debug output anywhere.
- **`--region us-east-1` on everything** because the tutorial said so. Pick
  a region close to your users; only put global-only resources in us-east-1.
- **One giant IAM role** that every Lambda assumes. Per-function roles are
  cheap and dramatically narrow blast radius.
- **Skipping retention on CloudWatch Logs.** Default is forever. Bills add up.
- **Storing prod and dev in the same account.** Use AWS Organizations and
  separate accounts. The blast radius justifies the friction.
- **Hand-clicking in the console for prod changes.** Use IaC (CDK / Terraform
  / SAM) once anything matters. Even bash scripts beat clicks.
- **Forgetting `--cli-binary-format raw-in-base64-out`** on Lambda invoke
  in CLI v2 — it expects base64 by default and will mangle JSON payloads.
- **Not tagging.** Untagged resources are invisible in Cost Explorer
  breakdowns. Tag at creation, enforce with SCPs.

---

## Data Model

**Account** — the unit of isolation, billing, and IAM trust. 12-digit ID.

**Region** — a geographic cluster of 3+ Availability Zones. Resources are
region-scoped except for IAM, Route53, CloudFront, WAF (CloudFront), and
S3 bucket namespace.

**Availability Zone (AZ)** — one or more discrete data centers within a
region. AZ IDs (`use1-az1`) are stable across accounts; AZ names (`us-east-1a`)
are randomized per account.

**ARN** — `arn:aws:<service>:<region>:<account>:<resource>`. Some have a
type prefix: `arn:aws:iam::123456789012:role/eos-deploy`. Memorize the
shape; you will write a lot of them.

**Principal** — anything that can make an API call. IAM user, IAM role,
federated user, AWS service (`lambda.amazonaws.com`).

**Policy** — JSON document of statements. Five types:
1. **Identity-based** — attached to user/role/group, says "this principal can do X."
2. **Resource-based** — attached to a bucket/queue/key, says "these principals can do X to me."
3. **Permission boundary** — max permissions a role can ever have.
4. **SCP** (Service Control Policy) — Org-level guardrail, denies cannot be overridden.
5. **Session policy** — passed at AssumeRole time, intersected with role policy.

**Effective permission** = identity policy ∩ resource policy ∩ SCP ∩
permission boundary ∩ session policy. Any explicit `Deny` wins.

**S3 object** = bucket + key + version + metadata + body. Buckets are flat;
"folders" are a console fiction over `/`-separated keys.

**EC2 instance** = AMI + instance type + ENIs + EBS volumes + security
groups + key pair + tags. Stoppable (EBS-backed) or not (instance-store).

**Lambda function** = code package (zip or container image) + runtime + handler
+ exec role + env vars + layers + concurrency settings + triggers.

---

## Webhooks and Events

**N/A in the conventional sense.** AWS does not "send webhooks" the way
Stripe or GitHub do. Instead AWS exposes:

- **EventBridge** — the canonical AWS-internal event bus. Every service
  emits events; rules pattern-match and route to targets (Lambda, SQS, SNS,
  Step Functions, API destinations). EventBridge **API Destinations** are
  the closest thing to outbound webhooks: a rule POSTs JSON to an external
  HTTPS endpoint with stored credentials.
- **SNS** — fan-out pub/sub. Topics, subscriptions (HTTPS, email, SMS,
  Lambda, SQS). HTTPS subscription requires a one-time confirmation handshake.
- **SQS** — pull-based queue. Messages persist 1 minute to 14 days.
  Long-polling reduces empty receives. Visibility timeout is the lock window.
- **S3 Event Notifications** — bucket-level triggers on PutObject,
  ObjectRemoved, etc., delivered to SNS, SQS, Lambda, or EventBridge.
- **CloudWatch Events** — the legacy name for what is now EventBridge
  default bus. Same thing, same API.

To **receive** a webhook from a third party (Stripe, Twilio, GitHub):

- **Lambda Function URL** — simplest. One HTTPS endpoint per function, no
  API Gateway needed. Free, AWS-managed TLS, optional IAM auth.
- **API Gateway HTTP API** — when you need routing, custom domains, JWT auth,
  WAF integration, request validation.

To **send** an event-like notification out of AWS:

- **SNS HTTPS subscription** — fire-and-forget POST with retry.
- **EventBridge API Destination** — more control, rate limiting, transformations.

---

## Limits

- **AWS account-wide service quotas** — most are soft and raisable via
  Service Quotas console.
- **S3**: 100 buckets per account default (raisable to 1,000), unlimited
  objects per bucket, 5 TB max object size, 5 GB max single PUT.
- **EC2**: vCPU-based limits per family (e.g., Standard On-Demand 32 vCPU
  default in new accounts). Spot has separate quotas.
- **Lambda**: 1,000 concurrent executions default, 15-minute max duration,
  10 GB max memory, 10 GB max ephemeral `/tmp`, 250 MB unzipped deployment
  package, 10 GB max container image.
- **IAM**: 5,000 users per account, 1,000 roles per account (raisable),
  10 managed policies per role/user/group default, 6,144 char inline policy.
- **CloudWatch Logs**: 1 MB max log event, 5 PutLogEvents/sec/stream.
- **SSM Parameter Store**: 10,000 standard params free, 4 KB standard /
  8 KB advanced value size, advanced params $0.05/param/month.
- **STS**: AssumeRole session 15 min – 12 hr (default 1 hr); SSO max 12 hr.

---

## Cost Model

The five expensive things, ranked by frequency of surprise:

1. **NAT Gateway** — $0.045/hr ($32/mo) + $0.045/GB processed. Forgotten in
   dev VPCs forever.
2. **Data transfer OUT to internet** — $0.09/GB after first GB. Cross-region
   is also $0.02/GB. Cross-AZ is $0.01/GB each direction.
3. **EBS volumes** — $0.08/GB-month gp3, snapshots $0.05/GB-month. Old
   snapshots from terminated instances accrue forever.
4. **CloudWatch Logs ingest** — $0.50/GB ingest + storage. Verbose Lambda
   logging without retention is the classic hit.
5. **Idle resources** — Elastic IPs not attached ($0.005/hr), idle RDS,
   idle load balancers (~$16/mo each), unused provisioned capacity.

Cheap things people are afraid of: **S3 storage** ($0.023/GB-month standard),
**Lambda invocations** ($0.20/M requests + $0.0000166667/GB-sec compute),
**SSM standard parameters** (free up to 10K), **CloudWatch metrics**
(first 10 free, then $0.30 each), **STS calls** (free).

Free tier (12 months for new accounts only):
- 750 hr/month t2.micro or t3.micro
- 5 GB S3 standard
- 1M Lambda requests + 400K GB-sec
- 25 GB DynamoDB
**Expires after 12 months without warning.**

Always-free: 1M Lambda req/mo, 25 GB DynamoDB, 10 CW custom metrics, 1M
SNS publishes, 1M SQS requests, 10K SSM std params.

---

## Version Pinning

- **AWS CLI v2** — single binary, bundled Python. Install via the official
  installer, not pip. Self-updates with `aws --version` shipping every
  ~2 weeks. CLI v1 is **deprecated** as of 2024; migrate immediately if
  still on it.
- **boto3 / botocore** — pin to a minor version range in `requirements.txt`:
  `boto3>=1.35,<1.36`. Botocore is auto-pulled. They release weekly with new
  service features and occasional API additions.
- **Python runtime** — Lambda supports python3.9, 3.10, 3.11, 3.12, 3.13.
  3.8 is end-of-life as of 2024; AWS deprecated the runtime. Use 3.12 by
  default.
- **boto3 in Lambda** — the runtime ships a boto3 version that lags by
  weeks. If you need a newer feature, bundle boto3 in your deployment package
  or layer.
- **Region opt-in** — newer regions (af-south-1, me-south-1, eu-south-1,
  ap-east-1, me-central-1, ap-southeast-3, etc.) require explicit opt-in
  per account.
- **API versions** — botocore handles per-service API versioning internally.
  You don't pick. SDK upgrade = API upgrade.

---

## Design Intent and Tradeoffs

AWS was built around three principles that explain almost every design choice:

1. **APIs first, primitives over products.** Every service is an HTTP API
   from day one. Higher-level products (Elastic Beanstalk, Amplify, App
   Runner) are wrappers that sit on top of the same primitives. The
   primitives (EC2, S3, IAM, VPC) outlive every wrapper.
2. **Eventual consistency by default, strong when forced.** S3 went strongly
   consistent in December 2020 — before that, even read-after-write was
   eventual. DynamoDB defaults to eventually consistent reads (cheaper),
   strongly consistent on request. RDS / Aurora are strong by default.
3. **Pay for what you use, no commitments unless you ask.** On-demand is the
   default. Reserved Instances, Savings Plans, Spot are opt-in cost
   optimizations. The flip side: zero commitment means zero budget cap,
   which is why billing alarms matter.

**Tradeoffs you inherit:**

- **Breadth over depth** — 200+ services means there is always 3 ways to do
  anything, and the right one isn't obvious. Documentation sprawl is real.
- **Backwards compatibility forever** — APIs from 2006 still work. Costs:
  legacy footguns (S3 path-style URLs, SigV2, IMDSv1) ship by default in
  some clients.
- **Console vs API drift** — the console is its own product with its own
  bugs and its own UX changes. Trust the API.
- **Security defaults improving but slowly** — public S3 buckets were a
  default until 2018. Block-public-access default-on shipped 2023.

---

## Problem-Solution Map and Hidden Capabilities

**"I need to share a private file with someone temporarily."**
→ S3 presigned URL, expires in seconds you specify. Don't make the bucket public.

**"I need a public webhook endpoint."**
→ Lambda Function URL (cheapest, simplest). API Gateway HTTP API if you
need routing/auth/throttling/custom domain.

**"I need a cron job in the cloud."**
→ EventBridge Scheduler (newer, recommended) or EventBridge rule with cron
expression → Lambda target. NOT a long-running EC2 with crond.

**"I need to run a one-shot batch job."**
→ Lambda if < 15 min and < 10 GB. AWS Batch or Fargate ECS task otherwise.
Step Functions to orchestrate multiple steps.

**"I need to copy 10 TB of objects between buckets/accounts."**
→ S3 Batch Operations or `aws s3 sync` with `--cli-read-timeout 0`. NOT
download-then-upload.

**"I need to grep through 100 GB of logs."**
→ CloudWatch Logs Insights for recent stuff (limited to 20 log groups,
queries timeout at 15 min). Athena over S3-exported logs for historical.

**"I need to run code on every S3 upload."**
→ S3 Event Notification → Lambda. Or → EventBridge → Lambda for filtering.

**"I need to keep a secret out of code."**
→ SSM Parameter Store SecureString (free, 10K params). Secrets Manager only
if you need automatic rotation ($0.40/secret/month).

**"My Lambda needs to talk to a private VPC resource."**
→ Configure Lambda VPC settings. Costs: cold-start ENI attachment, requires
NAT for internet access. Reconsider whether the resource needs to be private.

**"I need a low-latency key-value store."**
→ DynamoDB (managed, single-digit ms). ElastiCache Redis if you already have
SQL elsewhere. Avoid running Redis on EC2 yourself unless you must.

**Hidden capabilities most people miss:**

- **S3 Object Lambda** — transform data on the fly during GET (resize images, redact PII).
- **S3 Multi-Region Access Points** — single global endpoint that routes to nearest replica.
- **Lambda SnapStart** — sub-second cold starts for Java (and now Python 3.12+).
- **EventBridge Pipes** — point-to-point source→filter→enrich→target without writing Lambda glue.
- **IAM Access Analyzer** — finds resources shared outside your account/org automatically.
- **AWS Nitro Enclaves** — encrypted compute environments for handling secrets that even root can't read.
- **Instance Connect Endpoint** — SSH to EC2 in private subnets without bastion or IGW.
- **Session Manager** — shell into any EC2 with the SSM agent without SSH/keys/SGs at all.

---

## Operational Behavior and Edge Cases

- **Eventual consistency in IAM**: a freshly created role can take seconds to
  minutes to be assumable. Race condition on automation. Add a retry loop
  with backoff after `CreateRole` + `PutRolePolicy`.
- **S3 bucket deletion requires emptying first** including all object
  versions and delete markers. `aws s3 rb --force` handles non-versioned;
  versioned buckets need the lifecycle rule trick or boto3 paginated delete.
- **EC2 `stop` vs `terminate`**: stop preserves the instance and root EBS,
  you keep paying for storage. Terminate deletes the instance; root EBS
  goes only if `DeleteOnTermination=true`.
- **Instance type families have different network performance** at the same
  vCPU count. `t4g` is burstable; `c7g` has guaranteed bandwidth.
- **Lambda /tmp is per-execution-environment**, not per-invocation. State
  leaks across warm invocations within the same container. Treat as cache.
- **Lambda env vars are visible to anyone with `lambda:GetFunctionConfiguration`**.
  Use SSM SecureString or Secrets Manager and read at cold start instead.
- **CloudWatch metric latency** — alarms fire on 1-5 minute delay even at
  1-minute resolution. Don't expect sub-minute reaction.
- **CloudTrail is region-scoped** by default. Enable a multi-region trail
  in one region to capture global activity (IAM, S3 data events, etc.).
- **S3 versioning is one-way** — once enabled you can suspend but not
  remove. Deleted objects become delete markers, not actually gone.
- **KMS key policies are layered** — even an admin needs explicit key
  policy access. Lock yourself out of a CMK and only support can recover it.
- **Service-linked roles** — some services (Auto Scaling, ECS) auto-create
  IAM roles in your account. Don't delete them or the service breaks.
- **Region-default DNS resolution** — Route53 private hosted zones don't
  cross VPC boundaries unless explicitly associated.

---

## Ecosystem Position and Composition

**AWS sits at the bottom** of most cloud stacks. Almost everything else
either runs ON AWS or competes WITH AWS:

- **Competitors at the IaaS level**: GCP, Azure, Oracle Cloud, Hetzner,
  DigitalOcean, Vultr, Linode. Hetzner / DO are 5–10x cheaper for steady
  workloads; AWS wins on breadth and managed services.
- **Sits under**: Vercel (Lambda + CloudFront under the hood), Netlify, Fly.io
  (AWS-adjacent), Heroku (AWS-hosted), Supabase (was AWS, moved), Neon
  (multi-cloud, includes AWS), most SaaS startups before they care.
- **Sits next to**: Cloudflare (CDN + Workers, often replaces CloudFront +
  Lambda@Edge), Tailscale (private overlay network, often replaces Site-to-Site
  VPN + bastion), GitHub Actions (CI, often replaces CodeBuild + CodePipeline).

**Tools that make AWS bearable:**

- **`aws-vault`** — keychain-backed credential storage, prompts for MFA,
  shells into a temporary subprocess with envs set. Use over plaintext keys.
- **`saml2aws` / `aws-sso-util`** — SSO ergonomics improvements.
- **Terraform / OpenTofu** — multi-cloud IaC, the de facto standard.
- **AWS CDK** — TypeScript/Python IaC that compiles to CloudFormation.
  Better than raw YAML, worse than Terraform for multi-cloud.
- **AWS SAM** — Lambda-specific IaC. Fine for pure Lambda apps.
- **`awscli-local`** + **LocalStack** — run AWS APIs locally for testing.
- **`s5cmd`** — 10x faster than `aws s3` for bulk operations.
- **`steampipe`** — query AWS as SQL. Underrated for inventory.

**Composition with EOS:**

- VPS (Tailscale-private) for primary compute and stateful services.
- Neon for Postgres (multi-cloud, AWS-hosted but managed).
- AWS S3 + CloudFront for public CDN-grade media when needed.
- AWS Lambda Function URL for inbound webhooks that can't terminate at the VPS.
- AWS SSM Parameter Store for secrets that AWS-side code reads.
- Cloudflare for everything DNS / WAF / public-facing TLS.
- GitHub Actions for CI; OIDC into AWS via short-lived role assumption.

---

## Trajectory and Evolution

**Where AWS is moving (2025–2026 horizon):**

- **IAM Identity Center is the new default.** Long-lived IAM users are being
  steadily de-emphasized in docs, console flows, and security guidance. New
  accounts get pushed toward Organizations + Identity Center from day one.
- **ARM (Graviton) by default.** `c7g`, `m7g`, `r7g`, `t4g` are price-perf
  winners. Lambda arm64 is ~20% cheaper than x86_64 with no perf penalty for
  most Python/Node workloads.
- **Bedrock as the AI gateway.** AWS's bet for the LLM era — managed access
  to Anthropic, Cohere, Mistral, Meta, Amazon Titan. Replaces the need to
  host models on EC2/SageMaker for most use cases. Pay-per-token.
- **EventBridge eating CloudWatch Events.** Same API, new name, more features.
  CloudWatch Events name is being phased out of docs.
- **Lambda SnapStart for Python.** Java was first; Python 3.12+ gets it
  next. Sub-second cold starts change the calculus for latency-sensitive
  Lambdas.
- **Aurora DSQL.** Serverless distributed Postgres-compatible database
  announced re:Invent 2024. Multi-region active-active. Competes with
  Spanner / CockroachDB / Neon.
- **S3 Express One Zone.** Single-AZ, ~10x faster, ~7x more expensive. For
  AI training data and analytics shuffles.
- **VPC Lattice.** Service mesh as a managed product. Cuts the need for
  service discovery + sidecars for many use cases.
- **Outposts and Local Zones expanding** for sub-millisecond latency
  workloads (gaming, AR, real-time bidding).

**What's being deprecated:**

- AWS CLI v1 (deprecated 2024), Lambda Python 3.8 / 3.9 (3.8 EOL), Node 16
  Lambda runtime, IMDSv1 (still default but discouraged), SigV2 signing,
  S3 path-style URLs (virtual-hosted-style is the path forward), AWS SDK
  for Java v1 (v2 GA), boto3 resource interface (frozen).

---

## Conceptual Model and Solution Recipes

**The mental model that makes AWS click:**

> AWS is a giant API surface. Every action you take — clicking the console,
> running `aws s3 cp`, calling boto3 — is a signed HTTPS request to a
> regional endpoint. IAM evaluates the request against policies; if it
> passes, the service does the work. The console is an app calling the same
> APIs you'd call. There is no "console magic." There is no "secret backend
> mode." Everything is the API.

If you accept this, then debugging AWS is just:

1. What API call is being made? (Use `--debug` or CloudTrail.)
2. What principal is making it? (`aws sts get-caller-identity`.)
3. What does the policy attached to that principal allow? (IAM Policy Simulator.)
4. What does the resource policy say? (Bucket policy, KMS key policy, etc.)
5. Are there SCPs / permission boundaries narrowing it? (Org admin can check.)
6. Is the request well-formed? (Signature, region, clock skew.)

### Solution recipes

**Recipe 1 — Public CDN-backed image hosting**

```
S3 bucket (private, BPA on)
  └── CloudFront distribution
        ├── Origin Access Control (OAC) — signed S3 requests
        ├── Custom domain via ACM cert in us-east-1
        ├── Cache policy: CachingOptimized
        └── Response headers policy: Security headers
```

EOS use: Lyfe Spectrum product imagery, Empyrean reels.

**Recipe 2 — Inbound webhook endpoint for a third party**

```
Lambda function (python3.12, arm64)
  ├── Function URL (NONE auth or AWS_IAM)
  ├── Reserved concurrency = 10 (DOS protection)
  ├── Env: SSM parameter ARN for the signing secret
  ├── Code: verify HMAC signature, parse, push to SQS
  └── Logs: /aws/lambda/eos-webhook-X with 14d retention
```

EOS use: Stripe webhooks, Twilio SMS, partner API callbacks.

**Recipe 3 — Scheduled job (replacement for cron-on-VPS)**

```
EventBridge Scheduler rule (cron(0 6 * * ? *) UTC)
  └── Target: Lambda function (or Step Function for multi-step)
        └── Dead-letter queue: SQS with 14d retention and CloudWatch alarm
```

EOS use: Don't. Run cron on the VPS unless the job needs AWS compute access.

**Recipe 4 — Secrets read from VPS code**

```
SSM Parameter Store
  └── /eos/prod/<key> (SecureString, KMS aws/ssm)

VPS code:
  boto3.client("ssm").get_parameter(Name="/eos/prod/X", WithDecryption=True)

IAM: dedicated user (or better, IAM Roles Anywhere) with policy:
  ssm:GetParameter on arn:aws:ssm:us-west-2:123:parameter/eos/prod/*
  kms:Decrypt on the SSM default key
```

EOS use: When EOS code needs an AWS-side secret. Otherwise stay on `.env`.

**Recipe 5 — Audit who did what**

```
CloudTrail: enable a multi-region trail to a dedicated S3 bucket in a
separate "log archive" account. Enable log file validation. Set bucket
lifecycle to Glacier after 90d, delete after 7y.

For real-time alerts: CloudTrail → EventBridge → SNS on specific patterns
(IAM user creation, root login, S3 bucket policy changes).
```

---

## Industry Expert and Cutting-Edge Usage

What teams operating AWS at scale do that small operators usually skip — and
which are worth borrowing even at small scale:

- **AWS Organizations from day one.** Even solo. Create a management
  account, a security/audit account, and one workload account per env.
  Costs nothing extra; massively improves blast radius and IAM hygiene.
  Borrow this.
- **Service Control Policies (SCPs)** — org-level guardrails: deny region X,
  deny `iam:DeleteRole`, deny disabling CloudTrail. Cannot be overridden by
  account admins. Borrow this.
- **OIDC federation from CI** — GitHub Actions assumes an AWS role via OIDC,
  no long-lived keys ever stored in CI secrets. Borrow this immediately.
- **Permission boundaries on every IAM role** — explicit max-permissions
  ceiling. Even if a role gets a broad policy attached by mistake, the
  boundary clamps it. Borrow at moderate scale.
- **`aws-vault exec`** for every interactive session, never bare envs.
  Borrow this.
- **Cost allocation tags + Cost Categories.** Tag every resource with
  `Project`, `Env`, `Owner`. Cost Categories group spend by tag patterns.
  Borrow at the first $100/month.
- **CloudFormation StackSets / Terraform workspaces** for multi-account
  baseline (CloudTrail, GuardDuty, Config, IAM Identity Center assignments).
- **GuardDuty** — managed threat detection on CloudTrail / VPC flow logs /
  DNS. ~$1–5/month at small scale. Borrow once you have anything sensitive.
- **AWS Config rules** — continuous compliance checks ("no public buckets,"
  "MFA on root"). Costs add up fast at scale; borrow selectively.
- **Athena over CloudTrail logs** — SQL forensics. Cheap, powerful.
- **Step Functions for any multi-step Lambda workflow.** People reach for
  Lambda-calls-Lambda which is an antipattern. Step Functions handles the
  orchestration, retries, error branches.
- **Provisioned Concurrency or SnapStart on user-facing Lambdas.** Cold
  starts kill UX.
- **Spot for non-critical compute** — 70–90% cheaper than on-demand if you
  can tolerate interruption.
- **Savings Plans** at >$100/month steady state — 1y or 3y commit, ~30–50%
  off compute.

---

## EOS Usage Patterns

EOS is a small-footprint, single-operator system. The AWS posture is
intentionally minimal. Ranked by likelihood of actual use:

**Pattern 1 — S3 + CloudFront for public media (HIGH likelihood)**

When Lyfe Spectrum needs product imagery served globally, or Empyrean
Studio needs reel hosting that an embed code can hit:

- One bucket per brand: `eos-lyfespectrum-media`, `eos-empyrean-media`
- Block public access ON
- CloudFront in front with OAC
- ACM cert in us-east-1 for the brand domain
- Cache policy: CachingOptimized, default TTL 24h
- Brand domain CNAME → CloudFront distribution

**Pattern 2 — Lambda Function URL for inbound webhooks (MEDIUM likelihood)**

Stripe, Twilio, partner APIs that need a stable public URL:

- One Lambda per integration, never a "generic webhook receiver"
- Per-function IAM exec role with least privilege
- Verify the signing secret on every invocation
- Push validated events to SQS, return 200 immediately
- VPS-side worker pulls SQS via boto3 long-polling

**Pattern 3 — SSM Parameter Store for AWS-side secrets (LOW likelihood)**

Only when AWS-side code needs a secret. Otherwise stay on `.env` on the VPS.

- Path convention: `/eos/<env>/<service>/<key>`
- SecureString with the default `aws/ssm` KMS key
- Read at cold start, cache in process memory

**Pattern 4 — Billing hygiene (always on)**

Even if AWS usage is zero:

- Three billing alarms: $20, $50, $100, all in us-east-1
- SNS topic → email afm
- Cost Explorer enabled (free)
- Monthly review on the first of the month: anything I don't recognize?
- Tag every resource at creation; untagged is invisible in breakdowns

**Pattern 5 — IAM discipline (always on)**

- Root account: hardware MFA, password in offline vault, never used
- IAM Identity Center: one user (afm), one permission set (`AdministratorAccess`),
  scoped to the one workload account
- One role per Lambda, one role per service
- Per-resource tagging policy: every resource needs `Project=eos`

**Pattern 6 — When AWS is the WRONG answer (most of the time)**

- Long-running services → VPS, not EC2 (10x cheaper)
- Postgres → Neon, not RDS (much cheaper, easier)
- Cron jobs → systemd timers on VPS, not EventBridge
- Inter-service comms → Tailscale + plain HTTP, not API Gateway
- Object storage for internal use → VPS disk, not S3
- Logs for internal services → journald + Loki on VPS, not CloudWatch
- LLM calls → Anthropic / Gemini direct, not Bedrock (until volume justifies)

The default answer to "should I put this on AWS?" is **no**. AWS earns its
place per workload, not by default.

---

## Gotchas

This is the long-form failure catalog. The SKILL.md gotchas list is the
short version; this one is exhaustive and grouped by service.

**IAM / STS / Identity**

- New role / new policy → 5–60 second propagation delay before assumable. Race condition in scripted setup.
- AssumeRole `DurationSeconds` cannot exceed the role's `MaxSessionDuration` (default 1h, raise on the role).
- Chained role assumption (role → role → role) maxes at 1 hour regardless of role's MaxSessionDuration.
- `iam:PassRole` is its own permission. Even if you can create a Lambda, you can't attach a role to it without PassRole.
- Wildcard in `Resource` for IAM actions like `iam:CreateUser` is broader than you think — combined with `iam:AttachUserPolicy *` it's full account takeover.
- IAM Identity Center permission set updates require re-`aws sso login` to pick up new permissions.
- Federated user names from SSO include `@` and weird chars — escape in resource ARNs.
- Root account has no policy that can deny it. SCPs do not apply to root in the management account.

**S3**

- Bucket names global across all of AWS, not per-account.
- Bucket region must be specified at create time and is immutable.
- `aws s3 sync --delete` direction is source → dest; reverse it and you nuke the wrong side.
- `aws s3 cp` does not preserve `Content-Type` for unknown extensions; set explicitly.
- `aws s3 ls s3://bucket/folder` shows nothing if no object key starts with `folder/`. There are no folders.
- Presigned URLs signed with temporary credentials (STS) expire when the credentials expire OR at the requested expiry, whichever is earlier.
- Versioning suspend ≠ disable. You cannot fully disable. Delete markers accumulate.
- `RequestPayer=requester` buckets refuse anonymous reads even via presigned URLs unless you set the header.
- Multipart uploads abandoned mid-flight cost storage. Set a lifecycle rule to abort incomplete multiparts after 7 days.

**EC2**

- Stopped instances still cost EBS storage.
- Terminated instances release EIPs only if EIPs were not allocated separately.
- Allocated-but-unattached EIPs cost $0.005/hr.
- Instance metadata IMDSv1 is SSRF-exploitable. Force v2 at launch and via account-level setting.
- Default VPCs in every region come with public subnets and IGWs. Unwanted attack surface in unused regions.
- Default security group allows all egress and intra-SG ingress. Don't use it for anything; create per-app SGs.
- Spot instances can be terminated with 2-minute warning. Don't put state on instance store.
- AMIs are region-scoped. Copy across regions before launching.

**Lambda**

- 15-minute hard limit. Async via SQS or Step Functions for longer work.
- 6 MB sync payload limit (request + response combined). Use S3 for larger.
- 256 KB async payload limit.
- Container images max 10 GB but cold-start scales with image size — keep slim.
- VPC-attached Lambdas need NAT for internet egress (or VPC endpoints for AWS APIs).
- Reserved concurrency of 0 = function is disabled. Common foot-shotgun.
- Provisioned concurrency costs even when idle.
- `lambda:InvokeFunction` does not include `lambda:InvokeFunctionUrl` — separate permission for Function URLs.

**CloudWatch**

- Log groups have no retention by default (= forever). Always set.
- Logs Insights queries are billed per GB scanned. Filter early in the pipeline.
- Custom metrics are $0.30 each per month. Cardinality explosions are expensive.
- Alarms in `INSUFFICIENT_DATA` state don't fire. New alarms start there for ~minutes.
- Alarm period must be ≥ metric publish frequency or the alarm flaps.
- Billing metrics only publish in `us-east-1` regardless of where you spend.

**CLI / boto3**

- `aws configure` writes plaintext keys. Never on shared machines.
- `--cli-binary-format` default in v2 is base64 — surprising on `lambda invoke`.
- `--query` runs client-side after pagination; `--filters` runs server-side. Use filters to save bytes.
- `boto3.client(...)` without `region_name` picks up env, then profile, then nothing (raises on first call).
- Resource interface (`boto3.resource`) is frozen. Don't use for new code.
- `botocore.exceptions.ClientError` wraps everything. Inspect `.response["Error"]["Code"]`.
- Default connect timeout 60s, read timeout 60s. Way too long for interactive use.
- HTTP keep-alive is on but socket count balloons under high concurrency. Use a `botocore.config.Config` with a `max_pool_connections`.

**Billing**

- Free tier expires 12 months after account creation, no warning.
- AWS does not stop spend at any threshold. Alarms are advisory.
- Cost Explorer data lags 24 hours.
- Cross-region data transfer is billable BOTH directions in some cases.
- Cross-AZ traffic is $0.01/GB each direction within a region.
- NAT Gateway is the #1 surprise bill, then idle ELBs, then EBS snapshots from terminated instances.
- Marketplace AMIs add per-hour fees on top of EC2 rates. Easy to miss.

**Region / endpoint**

- Newer regions require opt-in in account settings.
- `us-east-1` outages affect "global" services (IAM control plane, CloudFront config, Route53 changes) even if your workload is elsewhere.
- S3 path-style URLs are deprecated; virtual-hosted-style is the future. Old SDKs still default to path-style.
- VPC endpoints (Gateway for S3/DynamoDB, Interface for everything else) cut data transfer costs and avoid NAT.

**Clock and signing**

- System clock more than 5 minutes off → all requests fail with `RequestTimeTooSkewed`. Run NTP.
- SigV4 signing requires the exact region and service in the canonical request. Don't hand-roll signing; use the SDK.

---

End of best_practices.md. Next-wave skills should graduate individual services
out of this coarse skill once usage frequency justifies dedicated coverage.
