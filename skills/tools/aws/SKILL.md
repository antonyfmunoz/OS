<<<<<<< Updated upstream
---
name: aws
description: "Use when authenticating to AWS from CLI or boto3, configuring credentials/profiles/SSO, uploading or presigning S3 objects, launching or stopping EC2, deploying or invoking Lambda, querying CloudWatch Logs, setting billing alarms, assuming IAM roles via STS, reading SSM Parameter Store, or deciding whether to use AWS at all vs the Tailscale-private VPS."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://docs.aws.amazon.com/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "AWS API (service-versioned)"
sdk_version: "AWS CLI v2 2.17.x, boto3 1.35.x, botocore 1.35.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: AWS (Operator's-Eye View)

## What This Tool Does

AWS is a public cloud composed of ~200 services behind a single IAM-governed
API surface. You almost never use "AWS" — you use a small set of services with
shared auth, shared regions, shared billing, and a shared CLI. This skill is
the COARSE operator's view: enough to authenticate cleanly, move objects to S3,
run a Lambda or EC2 instance, read CloudWatch logs, and not get billed
$3,000 by accident. Per-service deep dives (full S3 lifecycle, Lambda cold-start
tuning, VPC networking, EKS, RDS, IAM policy authoring at scale) are explicitly
out of scope and deferred to future skill waves.

Core capabilities covered here:

- **IAM + STS** — users, roles, AssumeRole, identity-based vs resource-based policies, least privilege as a default posture
- **S3** — buckets, objects, presigned URLs, public-access blocks, lifecycle rules, server-side encryption
- **EC2 basics** — launch, stop, terminate, key pairs, security groups, instance metadata
- **Lambda** — zip and container-image functions, env vars, invoke, logs, IAM execution role
- **CloudWatch** — Logs (streams, groups, retention), Logs Insights queries, Metrics, Alarms
- **Billing hygiene** — Cost Explorer, Budgets, billing alarms, free-tier traps
- **AWS CLI v2** — profiles, SSO, named credential sources, output formats
- **boto3** — session vs client vs resource, credential chain, retries
- **SSM Parameter Store** — secrets and config without paying for Secrets Manager
- **IAM Identity Center (SSO)** — modern replacement for long-lived access keys

## EOS Integration

EOS runs on a Tailscale-private VPS at 100.77.233.50 with Neon for Postgres,
Docker for services, and zero AWS dependency by default. AWS is intentionally
peripheral. The decision criterion is:

**Reach for the VPS first. Reach for AWS only when one of these is true:**

1. **Public CDN-grade media delivery** — S3 + CloudFront for assets that need
   global edge caching (Lyfe Spectrum product photos, Empyrean reels). The VPS
   can serve them but cannot edge-cache them cheaply.
2. **Public webhook endpoint that cannot live behind Tailscale** — a third-party
   service (Stripe, Twilio, a partner API) needs to POST to a stable public URL
   and you don't want to expose the VPS. Lambda Function URL or API Gateway
   fronting Lambda is the right answer.
3. **Compliance / customer-data isolation** — when a client demands SOC2-style
   posture and Neon + VPS doesn't satisfy procurement.
4. **Ephemeral compute spikes** — batch image processing, video transcoding,
   one-shot training runs. Lambda or short-lived EC2 spot.

If none of those apply, **do not use AWS**. The VPS is faster, cheaper,
private by default, and has no surprise bill.

Canonical EOS AWS posture:

- **One AWS account**, root locked with hardware MFA, never used after setup
- **IAM Identity Center** (SSO) for human access; no long-lived IAM users
- **One profile per role** in `~/.aws/config`, `sso_session` based
- **Billing alarm at $20, $50, $100** before any service is enabled
- **`aws-vault` or env-only** for boto3 — never plaintext keys in `.env`
- **SSM Parameter Store** for any secret AWS-side code needs
- **Region pinned** to `us-west-2` (Portland-local, low latency from VPS)
- **Tag every resource** with `Project=eos`, `Env=prod|dev`, `Owner=afm`

## Authentication

AWS authentication is a **credential chain**, not a single mechanism. boto3
and AWS CLI v2 walk this chain in order and use the first source that resolves:

1. Explicit params (`boto3.client('s3', aws_access_key_id=...)`) — avoid
2. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_PROFILE`, `AWS_REGION`
3. `AWS_SHARED_CREDENTIALS_FILE` (`~/.aws/credentials`)
4. `AWS_CONFIG_FILE` (`~/.aws/config`) — profiles, SSO sessions, AssumeRole chains
5. Container credentials (`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`) — ECS / App Runner
6. **IMDSv2** — EC2 instance metadata, role attached to the instance

The modern correct path for a human on a laptop or VPS:

- IAM Identity Center (SSO) → `aws configure sso` → `aws sso login --profile X` →
  short-lived creds cached under `~/.aws/sso/cache/`, auto-refreshed by CLI/SDK.

The modern correct path for code on EC2/ECS/Lambda:

- Attach an IAM **role** to the compute. boto3 finds it via IMDSv2 or the
  container credential endpoint. Zero secrets on disk.

The wrong-but-still-everywhere path:

- Long-lived `AKIA...` access keys in `~/.aws/credentials` or `.env`. Rotate
  every 90 days, never commit, scope to one role, and plan to migrate off.

## Quick Reference

### Configure SSO (modern, correct)

```bash
aws configure sso
# SSO start URL: https://d-xxxxxxxxxx.awsapps.com/start
# SSO Region: us-west-2
# Pick account, pick role, set CLI default region us-west-2, output json

# Subsequent logins (12-hour token by default)
aws sso login --profile eos-admin

# Use the profile
export AWS_PROFILE=eos-admin
aws sts get-caller-identity
```

### S3 essentials

```bash
# Bucket create with public access fully blocked (default since 2023)
aws s3api create-bucket --bucket eos-media-prod \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2

aws s3api put-public-access-block --bucket eos-media-prod \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Upload, list, copy, delete
aws s3 cp ./photo.jpg s3://eos-media-prod/2026/04/photo.jpg
aws s3 ls s3://eos-media-prod/2026/04/
aws s3 sync ./local/ s3://eos-media-prod/sync/ --delete
aws s3 rm s3://eos-media-prod/2026/04/photo.jpg

# Presigned URL — share a private object for N seconds
aws s3 presign s3://eos-media-prod/2026/04/photo.jpg --expires-in 3600
```

### EC2 minimal lifecycle

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
  --output table

aws ec2 stop-instances  --instance-ids i-0abc123
aws ec2 start-instances --instance-ids i-0abc123
aws ec2 terminate-instances --instance-ids i-0abc123
```

### Lambda deploy + invoke (zip)

```bash
zip -r function.zip handler.py
aws lambda create-function --function-name eos-webhook \
  --runtime python3.12 --handler handler.lambda_handler \
  --role arn:aws:iam::123456789012:role/eos-lambda-exec \
  --zip-file fileb://function.zip --timeout 15 --memory-size 256

aws lambda update-function-code --function-name eos-webhook \
  --zip-file fileb://function.zip

aws lambda invoke --function-name eos-webhook \
  --payload '{"hello":"world"}' --cli-binary-format raw-in-base64-out out.json
cat out.json
```

### CloudWatch Logs Insights

```bash
aws logs start-query \
  --log-group-name /aws/lambda/eos-webhook \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50'

aws logs get-query-results --query-id <id-from-above>
```

### Billing alarm (pre-flight before enabling anything)

```bash
# Enable billing metrics in us-east-1 (alarms live there even for us-west-2 spend)
aws cloudwatch put-metric-alarm --region us-east-1 \
  --alarm-name eos-billing-50usd \
  --alarm-description "EOS monthly spend exceeded $50" \
  --metric-name EstimatedCharges --namespace AWS/Billing \
  --statistic Maximum --period 21600 --evaluation-periods 1 \
  --threshold 50 --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:billing-alerts
```

### STS AssumeRole

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/eos-deploy \
  --role-session-name afm-cli \
  --duration-seconds 3600
# Capture AccessKeyId / SecretAccessKey / SessionToken from JSON, export them
```

### SSM Parameter Store (cheap secrets)

```bash
aws ssm put-parameter --name /eos/prod/openai_key \
  --value "sk-..." --type SecureString --overwrite

aws ssm get-parameter --name /eos/prod/openai_key --with-decryption \
  --query Parameter.Value --output text
```

### boto3 minimal pattern

```python
import boto3
session = boto3.Session(profile_name="eos-admin", region_name="us-west-2")
s3 = session.client("s3")
s3.upload_file("photo.jpg", "eos-media-prod", "2026/04/photo.jpg")
url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": "eos-media-prod", "Key": "2026/04/photo.jpg"},
    ExpiresIn=3600,
)
```

## Conceptual Model

**AWS is IAM with services bolted on.** Every API call is `(principal, action,
resource, condition) → allow|deny`. Get IAM right and everything else is
mechanical. Get IAM wrong and you either can't do your job or you're on the
front page of HackerNews.

**Region is physical, account is logical, principal is who, role is what-they-can-do.**
Resources live in a region (S3 buckets, EC2 instances, Lambda functions —
even though some have global names). Accounts are isolation boundaries: blast
radius, billing, and IAM trust all stop at the account edge. A principal is
a human or a workload; a role is a hat a principal puts on temporarily via STS.

**Short-lived credentials beat long-lived keys, always.** SSO tokens, instance
roles, and AssumeRole produce credentials that expire in minutes-to-hours.
Long-lived `AKIA...` keys are the leak vector behind nearly every public AWS
breach. Treat them like radioactive material: tag, rotate, prefer to delete.

**Billing is a backpressure system, not a budget system.** AWS will not stop
you from spending. You set alarms; the alarms tell you after the fact. Set
them BEFORE you enable services, not after the first bill arrives.

If you internalize this, the confusing parts collapse:

- "Why can't my Lambda read S3?" → execution role has no `s3:GetObject` on that resource ARN
- "Why is my S3 bucket public?" → block-public-access not enabled, or a bucket policy overrides it
- "Why did I get billed $400 for nothing?" → NAT Gateway hourly + data processing, or cross-region transfer, or a forgotten EBS volume

## Gotchas

- **`us-east-1` is special.** Billing metrics, CloudFront, IAM, Route53, ACM
  certs for CloudFront — all live in `us-east-1`. Your default region can be
  `us-west-2` and you still need `--region us-east-1` for these.
- **S3 bucket names are globally unique** across all AWS accounts on Earth.
  Pick names with your org slug: `eos-media-prod`, not `media-prod`.
- **NAT Gateway is $0.045/hour + $0.045/GB processed** — ~$33/month minimum
  even idle. A single forgotten NAT in a dev VPC is the #1 surprise bill.
- **EBS volumes are NOT deleted** when you terminate an EC2 instance unless
  `DeleteOnTermination=true` was set at launch. Old volumes accrue forever.
- **IMDSv1 is still default on some old AMIs** — SSRF exfiltration vector.
  Force IMDSv2: `--metadata-options HttpTokens=required`.
- **`aws s3 sync --delete` on the wrong direction** wipes your local or your
  bucket. Always dry-run first: `--dryrun`.
- **Lambda cold starts** for Python with heavy imports (boto3, pandas) are
  multi-second. Use Lambda layers, slim deps, or provisioned concurrency.
- **CloudWatch Logs cost more than the compute** if you log verbosely without
  retention. Default retention is **never expire**. Set it: `aws logs put-retention-policy --log-group-name X --retention-in-days 14`.
- **`aws configure` writes plaintext keys** to `~/.aws/credentials`. Prefer
  `aws configure sso`. If you must use keys, use `aws-vault` to keep them in
  the OS keychain.
- **SSO token expires every 12 hours** and the SDK will throw
  `TokenRetrievalError` mid-script. Catch it and prompt re-login or use a
  longer session in `~/.aws/config`.
- **boto3 default retries are 4 with exponential backoff** — looks like a
  hang on throttled APIs. Configure `retries={"max_attempts": 10, "mode": "adaptive"}`.
- **Public access block has TWO layers** — account-level and bucket-level.
  Both must be set. Default since April 2023 is "all blocked" for new
  buckets, but old accounts may not have account-level set.
- **Region drift** — `AWS_REGION` vs `AWS_DEFAULT_REGION` vs profile region
  vs explicit `--region`. Order of precedence is: explicit flag > env >
  profile. Don't trust your shell.
- **Free tier expires after 12 months.** The free t2.micro you launched as
  a student becomes $8/month on month 13 with no warning except the bill.

See references/best_practices.md for the full 19-section creator-level knowledge base.

---

## Skill Decomposition Notice

This is an **intentionally coarse operator skill**. It treats AWS as one tool
because at the EOS scale (peripheral usage, single account, single operator)
that is the right granularity. Per-service deep dives — full S3 lifecycle and
replication, Lambda performance tuning and container images at scale, VPC
and networking, IAM policy authoring patterns, RDS, EKS, Step Functions,
Bedrock, EventBridge, SQS, SNS, DynamoDB, CloudFormation/CDK/Terraform — are
**deferred to future skill waves**. When EOS usage of any specific service
crosses the threshold of "I'm doing this weekly and getting bitten by
service-specific gotchas," create `/opt/OS/skills/tools/aws-<service>/`
and graduate that service to its own skill.
=======
---
name: aws
description: "Use when authenticating to AWS from CLI or boto3, configuring credentials/profiles/SSO, uploading or presigning S3 objects, launching or stopping EC2, deploying or invoking Lambda, querying CloudWatch Logs, setting billing alarms, assuming IAM roles via STS, reading SSM Parameter Store, or deciding whether to use AWS at all vs the Tailscale-private VPS."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://docs.aws.amazon.com/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "AWS API (service-versioned)"
sdk_version: "AWS CLI v2 2.17.x, boto3 1.35.x, botocore 1.35.x"
speed_category: stable
---

# Tool: AWS (Operator's-Eye View)

## What This Tool Does

AWS is a public cloud composed of ~200 services behind a single IAM-governed
API surface. You almost never use "AWS" — you use a small set of services with
shared auth, shared regions, shared billing, and a shared CLI. This skill is
the COARSE operator's view: enough to authenticate cleanly, move objects to S3,
run a Lambda or EC2 instance, read CloudWatch logs, and not get billed
$3,000 by accident. Per-service deep dives (full S3 lifecycle, Lambda cold-start
tuning, VPC networking, EKS, RDS, IAM policy authoring at scale) are explicitly
out of scope and deferred to future skill waves.

Core capabilities covered here:

- **IAM + STS** — users, roles, AssumeRole, identity-based vs resource-based policies, least privilege as a default posture
- **S3** — buckets, objects, presigned URLs, public-access blocks, lifecycle rules, server-side encryption
- **EC2 basics** — launch, stop, terminate, key pairs, security groups, instance metadata
- **Lambda** — zip and container-image functions, env vars, invoke, logs, IAM execution role
- **CloudWatch** — Logs (streams, groups, retention), Logs Insights queries, Metrics, Alarms
- **Billing hygiene** — Cost Explorer, Budgets, billing alarms, free-tier traps
- **AWS CLI v2** — profiles, SSO, named credential sources, output formats
- **boto3** — session vs client vs resource, credential chain, retries
- **SSM Parameter Store** — secrets and config without paying for Secrets Manager
- **IAM Identity Center (SSO)** — modern replacement for long-lived access keys

## EOS Integration

EOS runs on a Tailscale-private VPS at 100.77.233.50 with Neon for Postgres,
Docker for services, and zero AWS dependency by default. AWS is intentionally
peripheral. The decision criterion is:

**Reach for the VPS first. Reach for AWS only when one of these is true:**

1. **Public CDN-grade media delivery** — S3 + CloudFront for assets that need
   global edge caching (Lyfe Spectrum product photos, Empyrean reels). The VPS
   can serve them but cannot edge-cache them cheaply.
2. **Public webhook endpoint that cannot live behind Tailscale** — a third-party
   service (Stripe, Twilio, a partner API) needs to POST to a stable public URL
   and you don't want to expose the VPS. Lambda Function URL or API Gateway
   fronting Lambda is the right answer.
3. **Compliance / customer-data isolation** — when a client demands SOC2-style
   posture and Neon + VPS doesn't satisfy procurement.
4. **Ephemeral compute spikes** — batch image processing, video transcoding,
   one-shot training runs. Lambda or short-lived EC2 spot.

If none of those apply, **do not use AWS**. The VPS is faster, cheaper,
private by default, and has no surprise bill.

Canonical EOS AWS posture:

- **One AWS account**, root locked with hardware MFA, never used after setup
- **IAM Identity Center** (SSO) for human access; no long-lived IAM users
- **One profile per role** in `~/.aws/config`, `sso_session` based
- **Billing alarm at $20, $50, $100** before any service is enabled
- **`aws-vault` or env-only** for boto3 — never plaintext keys in `.env`
- **SSM Parameter Store** for any secret AWS-side code needs
- **Region pinned** to `us-west-2` (Portland-local, low latency from VPS)
- **Tag every resource** with `Project=eos`, `Env=prod|dev`, `Owner=afm`

## Authentication

AWS authentication is a **credential chain**, not a single mechanism. boto3
and AWS CLI v2 walk this chain in order and use the first source that resolves:

1. Explicit params (`boto3.client('s3', aws_access_key_id=...)`) — avoid
2. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_PROFILE`, `AWS_REGION`
3. `AWS_SHARED_CREDENTIALS_FILE` (`~/.aws/credentials`)
4. `AWS_CONFIG_FILE` (`~/.aws/config`) — profiles, SSO sessions, AssumeRole chains
5. Container credentials (`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`) — ECS / App Runner
6. **IMDSv2** — EC2 instance metadata, role attached to the instance

The modern correct path for a human on a laptop or VPS:

- IAM Identity Center (SSO) → `aws configure sso` → `aws sso login --profile X` →
  short-lived creds cached under `~/.aws/sso/cache/`, auto-refreshed by CLI/SDK.

The modern correct path for code on EC2/ECS/Lambda:

- Attach an IAM **role** to the compute. boto3 finds it via IMDSv2 or the
  container credential endpoint. Zero secrets on disk.

The wrong-but-still-everywhere path:

- Long-lived `AKIA...` access keys in `~/.aws/credentials` or `.env`. Rotate
  every 90 days, never commit, scope to one role, and plan to migrate off.

## Quick Reference

### Configure SSO (modern, correct)

```bash
aws configure sso
# SSO start URL: https://d-xxxxxxxxxx.awsapps.com/start
# SSO Region: us-west-2
# Pick account, pick role, set CLI default region us-west-2, output json

# Subsequent logins (12-hour token by default)
aws sso login --profile eos-admin

# Use the profile
export AWS_PROFILE=eos-admin
aws sts get-caller-identity
```

### S3 essentials

```bash
# Bucket create with public access fully blocked (default since 2023)
aws s3api create-bucket --bucket eos-media-prod \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2

aws s3api put-public-access-block --bucket eos-media-prod \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Upload, list, copy, delete
aws s3 cp ./photo.jpg s3://eos-media-prod/2026/04/photo.jpg
aws s3 ls s3://eos-media-prod/2026/04/
aws s3 sync ./local/ s3://eos-media-prod/sync/ --delete
aws s3 rm s3://eos-media-prod/2026/04/photo.jpg

# Presigned URL — share a private object for N seconds
aws s3 presign s3://eos-media-prod/2026/04/photo.jpg --expires-in 3600
```

### EC2 minimal lifecycle

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' \
  --output table

aws ec2 stop-instances  --instance-ids i-0abc123
aws ec2 start-instances --instance-ids i-0abc123
aws ec2 terminate-instances --instance-ids i-0abc123
```

### Lambda deploy + invoke (zip)

```bash
zip -r function.zip handler.py
aws lambda create-function --function-name eos-webhook \
  --runtime python3.12 --handler handler.lambda_handler \
  --role arn:aws:iam::123456789012:role/eos-lambda-exec \
  --zip-file fileb://function.zip --timeout 15 --memory-size 256

aws lambda update-function-code --function-name eos-webhook \
  --zip-file fileb://function.zip

aws lambda invoke --function-name eos-webhook \
  --payload '{"hello":"world"}' --cli-binary-format raw-in-base64-out out.json
cat out.json
```

### CloudWatch Logs Insights

```bash
aws logs start-query \
  --log-group-name /aws/lambda/eos-webhook \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50'

aws logs get-query-results --query-id <id-from-above>
```

### Billing alarm (pre-flight before enabling anything)

```bash
# Enable billing metrics in us-east-1 (alarms live there even for us-west-2 spend)
aws cloudwatch put-metric-alarm --region us-east-1 \
  --alarm-name eos-billing-50usd \
  --alarm-description "EOS monthly spend exceeded $50" \
  --metric-name EstimatedCharges --namespace AWS/Billing \
  --statistic Maximum --period 21600 --evaluation-periods 1 \
  --threshold 50 --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:billing-alerts
```

### STS AssumeRole

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/eos-deploy \
  --role-session-name afm-cli \
  --duration-seconds 3600
# Capture AccessKeyId / SecretAccessKey / SessionToken from JSON, export them
```

### SSM Parameter Store (cheap secrets)

```bash
aws ssm put-parameter --name /eos/prod/openai_key \
  --value "sk-..." --type SecureString --overwrite

aws ssm get-parameter --name /eos/prod/openai_key --with-decryption \
  --query Parameter.Value --output text
```

### boto3 minimal pattern

```python
import boto3
session = boto3.Session(profile_name="eos-admin", region_name="us-west-2")
s3 = session.client("s3")
s3.upload_file("photo.jpg", "eos-media-prod", "2026/04/photo.jpg")
url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": "eos-media-prod", "Key": "2026/04/photo.jpg"},
    ExpiresIn=3600,
)
```

## Conceptual Model

**AWS is IAM with services bolted on.** Every API call is `(principal, action,
resource, condition) → allow|deny`. Get IAM right and everything else is
mechanical. Get IAM wrong and you either can't do your job or you're on the
front page of HackerNews.

**Region is physical, account is logical, principal is who, role is what-they-can-do.**
Resources live in a region (S3 buckets, EC2 instances, Lambda functions —
even though some have global names). Accounts are isolation boundaries: blast
radius, billing, and IAM trust all stop at the account edge. A principal is
a human or a workload; a role is a hat a principal puts on temporarily via STS.

**Short-lived credentials beat long-lived keys, always.** SSO tokens, instance
roles, and AssumeRole produce credentials that expire in minutes-to-hours.
Long-lived `AKIA...` keys are the leak vector behind nearly every public AWS
breach. Treat them like radioactive material: tag, rotate, prefer to delete.

**Billing is a backpressure system, not a budget system.** AWS will not stop
you from spending. You set alarms; the alarms tell you after the fact. Set
them BEFORE you enable services, not after the first bill arrives.

If you internalize this, the confusing parts collapse:

- "Why can't my Lambda read S3?" → execution role has no `s3:GetObject` on that resource ARN
- "Why is my S3 bucket public?" → block-public-access not enabled, or a bucket policy overrides it
- "Why did I get billed $400 for nothing?" → NAT Gateway hourly + data processing, or cross-region transfer, or a forgotten EBS volume

## Gotchas

- **`us-east-1` is special.** Billing metrics, CloudFront, IAM, Route53, ACM
  certs for CloudFront — all live in `us-east-1`. Your default region can be
  `us-west-2` and you still need `--region us-east-1` for these.
- **S3 bucket names are globally unique** across all AWS accounts on Earth.
  Pick names with your org slug: `eos-media-prod`, not `media-prod`.
- **NAT Gateway is $0.045/hour + $0.045/GB processed** — ~$33/month minimum
  even idle. A single forgotten NAT in a dev VPC is the #1 surprise bill.
- **EBS volumes are NOT deleted** when you terminate an EC2 instance unless
  `DeleteOnTermination=true` was set at launch. Old volumes accrue forever.
- **IMDSv1 is still default on some old AMIs** — SSRF exfiltration vector.
  Force IMDSv2: `--metadata-options HttpTokens=required`.
- **`aws s3 sync --delete` on the wrong direction** wipes your local or your
  bucket. Always dry-run first: `--dryrun`.
- **Lambda cold starts** for Python with heavy imports (boto3, pandas) are
  multi-second. Use Lambda layers, slim deps, or provisioned concurrency.
- **CloudWatch Logs cost more than the compute** if you log verbosely without
  retention. Default retention is **never expire**. Set it: `aws logs put-retention-policy --log-group-name X --retention-in-days 14`.
- **`aws configure` writes plaintext keys** to `~/.aws/credentials`. Prefer
  `aws configure sso`. If you must use keys, use `aws-vault` to keep them in
  the OS keychain.
- **SSO token expires every 12 hours** and the SDK will throw
  `TokenRetrievalError` mid-script. Catch it and prompt re-login or use a
  longer session in `~/.aws/config`.
- **boto3 default retries are 4 with exponential backoff** — looks like a
  hang on throttled APIs. Configure `retries={"max_attempts": 10, "mode": "adaptive"}`.
- **Public access block has TWO layers** — account-level and bucket-level.
  Both must be set. Default since April 2023 is "all blocked" for new
  buckets, but old accounts may not have account-level set.
- **Region drift** — `AWS_REGION` vs `AWS_DEFAULT_REGION` vs profile region
  vs explicit `--region`. Order of precedence is: explicit flag > env >
  profile. Don't trust your shell.
- **Free tier expires after 12 months.** The free t2.micro you launched as
  a student becomes $8/month on month 13 with no warning except the bill.

See references/best_practices.md for the full 19-section creator-level knowledge base.

---

## Skill Decomposition Notice

This is an **intentionally coarse operator skill**. It treats AWS as one tool
because at the EOS scale (peripheral usage, single account, single operator)
that is the right granularity. Per-service deep dives — full S3 lifecycle and
replication, Lambda performance tuning and container images at scale, VPC
and networking, IAM policy authoring patterns, RDS, EKS, Step Functions,
Bedrock, EventBridge, SQS, SNS, DynamoDB, CloudFormation/CDK/Terraform — are
**deferred to future skill waves**. When EOS usage of any specific service
crosses the threshold of "I'm doing this weekly and getting bitten by
service-specific gotchas," create `/opt/OS/skills/tools/aws-<service>/`
and graduate that service to its own skill.
>>>>>>> Stashed changes
