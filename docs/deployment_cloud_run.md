# Deployment on Cloud Run

## Target Runtime

Primary deployment target:

- Cloud Run

Container responsibilities:

- run Streamlit on `0.0.0.0:$PORT`
- create `.streamlit/secrets.toml` from env vars when needed
- use the Cloud Run runtime service account for BigQuery access

## Local vs Cloud

### Local

- authentication config comes from `.streamlit/secrets.toml`
- BigQuery auth usually comes from `gcloud auth application-default login`
- app runs with `.\run_streamlit.ps1`

### Cloud Run

- auth values come from Secret Manager-backed env vars
- `scripts/bootstrap_streamlit_secrets.py` writes a runtime secrets file
- BigQuery auth comes from the Cloud Run runtime service account
- no local persistence is used

## Build and Push

Example flow:

```powershell
gcloud auth configure-docker southamerica-east1-docker.pkg.dev
docker build -t southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest .
docker push southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest
```

## Terraform Deployment

Set in `terraform.tfvars`:

- `deploy_cloud_run = true`
- `container_image = "southamerica-east1-docker.pkg.dev/ide-math-app/glipmath/glipmath:latest"`

Then apply:

```powershell
cd infrastructure/terraform/environments/dev
terraform init
terraform apply
```

## Cloud Run Defaults

The Terraform defaults are intentionally modest:

- CPU: `1`
- Memory: `512Mi`
- Concurrency: `20`
- Min instances: `0`
- Max instances: `2`
- Public ingress enabled

Public ingress is expected because authentication is handled inside the Streamlit app.

## Verification Checklist

- Cloud Run service reaches the login screen
- Google login redirects back to `/oauth2callback`
- authorized user enters main page
- non-whitelisted user sees denial screen
- answer submission inserts rows into BigQuery
- leaderboard view renders
