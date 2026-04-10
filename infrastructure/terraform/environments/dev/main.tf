locals {
  common_labels = merge(
    {
      app         = "glipmath"
      environment = var.environment
      managed_by  = "terraform"
    },
    var.labels
  )

  required_services = [
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "serviceusage.googleapis.com",
  ]
}

module "project_services" {
  source = "../../modules/project_services"

  project_id = var.project_id
  services   = local.required_services
}

module "service_accounts" {
  source = "../../modules/service_accounts"

  project_id           = var.project_id
  runtime_account_id   = var.runtime_service_account_id
  runtime_display_name = "GlipMath Streamlit BigQuery runtime"

  depends_on = [module.project_services]
}

module "bigquery" {
  source = "../../modules/bigquery"

  project_id                  = var.project_id
  location                    = var.bigquery_location
  core_dataset_id             = var.core_dataset_id
  events_dataset_id           = var.events_dataset_id
  analytics_dataset_id        = var.analytics_dataset_id
  question_bank_table_id      = var.question_bank_table_id
  user_access_table_id        = var.user_access_table_id
  answers_table_id            = var.answers_table_id
  leaderboard_view_id         = var.leaderboard_view_id
  user_totals_view_id         = var.user_totals_view_id
  user_daily_activity_view_id = var.user_daily_activity_view_id
  question_bank_schema        = file("${path.module}/../../schemas/question_bank.json")
  user_access_schema          = file("${path.module}/../../schemas/user_access.json")
  answers_schema              = file("${path.module}/../../schemas/answers.json")
  leaderboard_view_query = templatefile(
    "${path.module}/../../../../sql/views/v_leaderboard.sql",
    {
      project_id        = var.project_id
      analytics_dataset = var.analytics_dataset_id
    }
  )
  user_totals_view_query = templatefile(
    "${path.module}/../../../../sql/views/v_user_totals.sql",
    {
      project_id      = var.project_id
      core_dataset    = var.core_dataset_id
      events_dataset  = var.events_dataset_id
    }
  )
  user_daily_activity_view_query = templatefile(
    "${path.module}/../../../../sql/views/v_user_daily_activity.sql",
    {
      project_id     = var.project_id
      events_dataset = var.events_dataset_id
    }
  )
  labels = local.common_labels

  depends_on = [module.project_services]
}

resource "google_project_iam_member" "runtime_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${module.service_accounts.runtime_email}"
}

resource "google_bigquery_dataset_iam_member" "runtime_core_editor" {
  project    = var.project_id
  dataset_id = module.bigquery.core_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${module.service_accounts.runtime_email}"
}

resource "google_bigquery_dataset_iam_member" "runtime_events_editor" {
  project    = var.project_id
  dataset_id = module.bigquery.events_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${module.service_accounts.runtime_email}"
}

resource "google_bigquery_dataset_iam_member" "runtime_analytics_viewer" {
  project    = var.project_id
  dataset_id = module.bigquery.analytics_dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${module.service_accounts.runtime_email}"
}
