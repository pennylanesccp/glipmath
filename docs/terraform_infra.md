# Terraform Infrastructure

## Scope

Terraform provisions:

- required project APIs
- service accounts
- BigQuery datasets, tables, and views
- GCS bucket
- Secret Manager placeholders
- Artifact Registry Docker repository
- optional Cloud Run deployment

## Module Layout

Modules under `infrastructure/terraform/modules/`:

- `project_services`
- `service_accounts`
- `bigquery`
- `storage`
- `secrets`
- `artifact_registry`
- `cloud_run`

Environment root:

- `infrastructure/terraform/environments/dev/`

## Enabled APIs

- `serviceusage.googleapis.com`: enables other APIs
- `bigquery.googleapis.com`: BigQuery datasets, tables, queries
- `run.googleapis.com`: Cloud Run service
- `secretmanager.googleapis.com`: auth secret storage
- `artifactregistry.googleapis.com`: Docker image repository
- `iam.googleapis.com`: service accounts and IAM bindings
- `cloudbuild.googleapis.com`: future CI/CD and image build alignment

## Runtime IAM

The Cloud Run runtime service account gets:

- `roles/bigquery.jobUser` on the project
- `roles/bigquery.dataViewer` on `glipmath_core`
- `roles/bigquery.dataEditor` on `glipmath_events`
- `roles/bigquery.dataViewer` on `glipmath_analytics`
- `roles/secretmanager.secretAccessor` on auth secrets

This is enough for:

- reading questions
- reading whitelist users
- reading analytics views
- appending answer events
- reading Secret Manager-backed auth config

## Apply Order

Recommended order:

1. `terraform init`
2. `terraform plan`
3. `terraform apply` with `deploy_cloud_run = false`
4. populate Secret Manager secret versions manually
5. build and push the Docker image
6. set `deploy_cloud_run = true` and `container_image`
7. `terraform apply` again

## Notes

- Secret Manager values are intentionally not managed in Terraform state.
- Cloud Run is optional on the first apply because the service expects real secret versions and a real container image.
- BigQuery schemas are version-controlled JSON files, not inline ad hoc definitions.
