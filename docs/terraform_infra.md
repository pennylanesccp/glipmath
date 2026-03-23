# Terraform Infra

Terraform now manages only the GCP resources still useful for the Streamlit Community Cloud + BigQuery MVP.

## Managed Resources

- enabled project APIs
- one runtime service account
- BigQuery datasets
- BigQuery tables
- BigQuery views
- IAM bindings for least-privilege BigQuery access

## Modules

- `project_services`
- `service_accounts`
- `bigquery`

## Required APIs

- `bigquery.googleapis.com`
  - creates datasets, tables, and views
- `iam.googleapis.com`
  - creates the runtime service account
- `cloudresourcemanager.googleapis.com`
  - manages project-level IAM bindings
- `serviceusage.googleapis.com`
  - enables the required APIs

## BigQuery Resources

Datasets:

- `glipmath_core`
- `glipmath_events`
- `glipmath_analytics`

Tables:

- `glipmath_core.question_bank`
- `glipmath_core.user_access`
- `glipmath_events.answers`

Views:

- `glipmath_analytics.v_user_totals`
- `glipmath_analytics.v_user_daily_activity`
- `glipmath_analytics.v_leaderboard`

The `answers` table is day-partitioned by `answered_at_utc` and clustered by `user_email` and `id_question`.

## IAM Model

The Streamlit runtime service account gets:

- `roles/bigquery.jobUser` on the project
- `roles/bigquery.dataViewer` on `glipmath_core`
- `roles/bigquery.dataEditor` on `glipmath_events`
- `roles/bigquery.dataViewer` on `glipmath_analytics`

These permissions cover:

- reading questions
- reading `user_access`
- inserting answers
- reading leaderboard analytics

## Apply Flow

1. copy `terraform.tfvars.example` to `terraform.tfvars`
2. review project, region, location, and service account values
3. run `.\run_terraform.ps1 -Command plan`
4. run `.\run_terraform.ps1`
5. manually create a service account key for the created runtime service account
6. place the key values in Streamlit secrets locally and in Streamlit Community Cloud

The script runs `terraform init` before the requested command inside `infrastructure/terraform/environments/dev`.

## Notes

- Terraform does not create service account keys because that would place sensitive material in Terraform state.
- There is no Cloud Run, Artifact Registry, Secret Manager, or GCS bucket in the current MVP infrastructure scope.
