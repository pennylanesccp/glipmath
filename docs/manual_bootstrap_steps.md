# Manual Bootstrap Steps

## 1. Confirm the GCP Project

- project ID: `ide-math-app`
- billing is enabled
- you have permission to manage APIs, IAM, service accounts, and BigQuery

## 2. Authenticate for Terraform

```powershell
gcloud auth login
gcloud auth application-default login
```

## 3. Review Billing, Quotas, and Region

- confirm BigQuery usage is allowed for the project
- choose the BigQuery location you want to use
- the repo defaults to `southamerica-east1`, but it is configurable in Terraform

## 4. Create or Confirm the Google OAuth App

- configure the OAuth consent screen
- create a Web application OAuth client
- add redirect URIs:
  - `http://localhost:8501/oauth2callback`
  - `https://<your-streamlit-app-name>.streamlit.app/oauth2callback`
- add beta testers as OAuth test users if the app is not publicly published

## 5. Copy the Terraform Example Variables

```powershell
Copy-Item infrastructure/terraform/environments/dev/terraform.tfvars.example infrastructure/terraform/environments/dev/terraform.tfvars
```

Review at least:

- `project_id`
- `region`
- `bigquery_location`
- `runtime_service_account_id`

## 6. Apply Terraform

```powershell
cd infrastructure/terraform/environments/dev
terraform init
terraform apply
```

Expected resources:

- required APIs for BigQuery and IAM
- one runtime service account
- BigQuery datasets
- BigQuery tables
- BigQuery analytics views
- IAM bindings for the runtime service account

## 7. Create the Runtime Service Account Key Manually

Terraform creates the service account, but not the private key.

Create a JSON key manually for the runtime service account and handle it carefully. Do not commit it to the repository.

You can do this via the Google Cloud Console or `gcloud iam service-accounts keys create`.

## 8. Configure Local Streamlit Secrets

```powershell
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Populate:

- Google OAuth values under `[auth]`
- BigQuery config under `[gcp]` and `[bigquery]`
- optional Gemini config under `[ai]` if you want to run explanation enrichment
- the service account JSON fields under `[gcp_service_account]`

## 9. Prepare the Question Bank Input

Use:

- raw question files under `data/`
- or `sql/seeds/question_bank_template.jsonl`

Validate and load:

```powershell
python scripts/validate_question_bank.py --input-path data
python scripts/load_question_bank_to_bigquery.py --input-path data
```

The current raw CSV pipeline supports the vestibulinho flat-question format and converts it into the nested `question_bank` schema before load.

The load script skips invalid rows and writes a CSV report to `trash/question_bank_failed_rows.csv` by default. Override the report path with `--failed-rows-output` if needed.

The question bank load script replaces the current contents of the target table.

Optional synthetic answer data for local/dev testing:

```powershell
python scripts/backfill_local_dev_data.py --user-email ana@example.com
```

Optional offline Gemini enrichment:

```powershell
python scripts/enrich_question_explanations.py --dry-run --limit 10
python scripts/enrich_question_explanations.py --limit 50
```

## 10. Configure Streamlit Community Cloud

- connect the GitHub repository
- set the app entrypoint to `app/streamlit_app.py`
- paste the same secrets structure used locally into Streamlit Cloud secrets

## 11. Deploy and Verify

- deploy the Streamlit app
- test Google login
- answer at least one question
- confirm answers land in BigQuery
- if using Gemini enrichment, confirm explanation backfills land in `glipmath_core.question_bank`
- confirm the leaderboard loads
- confirm the question flow shows explanations correctly
