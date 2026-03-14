# Manual Bootstrap Steps

## 1. Create or Confirm the GCP Project

- confirm the project exists: `ide-math-app`
- confirm billing is enabled
- confirm you have permission to enable APIs and create service accounts

## 2. Authenticate Terraform

Example:

```powershell
gcloud auth login
gcloud auth application-default login
```

Use a principal that can manage:

- IAM
- BigQuery
- Cloud Run
- Secret Manager
- Artifact Registry
- GCS

## 3. Review Quotas and Region

- default region in this repo: `southamerica-east1`
- confirm BigQuery location is acceptable
- confirm Cloud Run and Artifact Registry should live in the same region

## 4. Create Google OAuth Consent and Client

Follow [docs/google_auth_setup.md](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/docs/google_auth_setup.md).

Prepare:

- local redirect URI
- Cloud Run redirect URI
- client ID
- client secret
- cookie secret

## 5. Prepare Terraform Variables

```powershell
cd infrastructure/terraform/environments/dev
Copy-Item terraform.tfvars.example terraform.tfvars
```

Fill any project-specific values.

For the first infra apply, keep:

- `deploy_cloud_run = false`

## 6. Apply Base Infrastructure

```powershell
terraform init
terraform plan
terraform apply
```

This creates:

- APIs
- service accounts
- BigQuery datasets/tables/views
- Secret Manager placeholders
- Artifact Registry
- GCS bucket

## 7. Populate Secret Manager Values

Add real secret versions for:

- OIDC client ID
- OIDC client secret
- redirect URI
- metadata URL
- cookie secret

## 8. Prepare CSV Seeds

Use the templates:

- [question_bank_template.csv](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/sql/seeds/question_bank_template.csv)
- [whitelist_template.csv](/c:/Users/Cliente/Documents/workspaces/personal/glipmath/sql/seeds/whitelist_template.csv)

Validate:

```powershell
python scripts/validate_question_bank.py
```

Load:

```powershell
python scripts/load_question_bank_to_bigquery.py
python scripts/load_whitelist_to_bigquery.py
```

Optional demo data:

```powershell
python scripts/backfill_local_dev_data.py
```

## 9. Build and Push the Container Image

```powershell
gcloud auth configure-docker southamerica-east1-docker.pkg.dev
docker build -t southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest .
docker push southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest
```

## 10. Enable Cloud Run Deployment in Terraform

Update `terraform.tfvars`:

- `deploy_cloud_run = true`
- `container_image = "southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest"`

Then apply again:

```powershell
terraform apply
```

## 11. Verify End to End

- open the Cloud Run URL
- confirm login works
- confirm whitelist enforcement works
- answer one question
- verify a new row appears in `glipmath_events.answers`
- verify leaderboard view reflects the new answer
