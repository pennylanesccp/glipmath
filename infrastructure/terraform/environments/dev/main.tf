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
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
  ]

  auth_secret_ids = [
    var.auth_cookie_secret_id,
    var.auth_client_id_secret_id,
    var.auth_client_secret_secret_id,
    var.auth_redirect_uri_secret_id,
    var.auth_server_metadata_url_secret_id,
  ]

  cloud_run_env_vars = {
    GLIPMATH_APP_NAME                    = "GlipMath"
    GLIPMATH_APP_VERSION                 = "0.1.0"
    GLIPMATH_ENVIRONMENT                 = var.environment
    GLIPMATH_TIMEZONE                    = "America/Sao_Paulo"
    GLIPMATH_GCP_PROJECT_ID              = var.project_id
    GLIPMATH_REGION                      = var.region
    GLIPMATH_CLOUD_RUN_SERVICE           = var.service_name
    GLIPMATH_BIGQUERY_CORE_DATASET       = var.core_dataset_id
    GLIPMATH_BIGQUERY_EVENTS_DATASET     = var.events_dataset_id
    GLIPMATH_BIGQUERY_ANALYTICS_DATASET  = var.analytics_dataset_id
    GLIPMATH_QUESTION_BANK_TABLE         = var.question_bank_table_id
    GLIPMATH_WHITELIST_TABLE             = var.whitelist_table_id
    GLIPMATH_ANSWERS_TABLE               = var.answers_table_id
    GLIPMATH_LEADERBOARD_VIEW            = var.leaderboard_view_id
    GLIPMATH_USER_TOTALS_VIEW            = var.user_totals_view_id
    GLIPMATH_USER_DAILY_ACTIVITY_VIEW    = var.user_daily_activity_view_id
  }

  cloud_run_secret_env_vars = {
    STREAMLIT_AUTH_COOKIE_SECRET       = var.auth_cookie_secret_id
    STREAMLIT_AUTH_CLIENT_ID           = var.auth_client_id_secret_id
    STREAMLIT_AUTH_CLIENT_SECRET       = var.auth_client_secret_secret_id
    STREAMLIT_AUTH_REDIRECT_URI        = var.auth_redirect_uri_secret_id
    STREAMLIT_AUTH_SERVER_METADATA_URL = var.auth_server_metadata_url_secret_id
  }
}

module "project_services" {
  source = "../../modules/project_services"

  project_id = var.project_id
  services   = local.required_services
}

module "service_accounts" {
  source = "../../modules/service_accounts"

  project_id                    = var.project_id
  runtime_account_id            = var.runtime_service_account_id
  runtime_display_name          = "GlipMath runtime service account"
  deploy_account_id             = var.deploy_service_account_id
  deploy_display_name           = "GlipMath deploy service account"
  create_deploy_service_account = var.create_deploy_service_account

  depends_on = [module.project_services]
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = var.artifact_repository_id
  description   = "Docker images for the GlipMath Streamlit app."
  labels        = local.common_labels

  depends_on = [module.project_services]
}

module "storage" {
  source = "../../modules/storage"

  project_id   = var.project_id
  location     = var.region
  bucket_name  = var.seed_bucket_name
  force_destroy = false
  labels       = local.common_labels

  depends_on = [module.project_services]
}

module "secrets" {
  source = "../../modules/secrets"

  project_id = var.project_id
  secret_ids = local.auth_secret_ids
  labels     = local.common_labels

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
  whitelist_table_id          = var.whitelist_table_id
  answers_table_id            = var.answers_table_id
  leaderboard_view_id         = var.leaderboard_view_id
  user_totals_view_id         = var.user_totals_view_id
  user_daily_activity_view_id = var.user_daily_activity_view_id
  question_bank_schema        = file("${path.module}/../../schemas/question_bank.json")
  whitelist_schema            = file("${path.module}/../../schemas/whitelist.json")
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
      project_id    = var.project_id
      core_dataset  = var.core_dataset_id
      events_dataset = var.events_dataset_id
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

resource "google_bigquery_dataset_iam_member" "runtime_core_viewer" {
  project    = var.project_id
  dataset_id = module.bigquery.core_dataset_id
  role       = "roles/bigquery.dataViewer"
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

resource "google_secret_manager_secret_iam_member" "runtime_secret_access" {
  for_each = toset(local.auth_secret_ids)

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.service_accounts.runtime_email}"
}

module "cloud_run" {
  count  = var.deploy_cloud_run ? 1 : 0
  source = "../../modules/cloud_run"

  project_id              = var.project_id
  region                  = var.region
  service_name            = var.service_name
  container_image         = var.container_image
  service_account_email   = module.service_accounts.runtime_email
  env_vars                = local.cloud_run_env_vars
  secret_env_vars         = local.cloud_run_secret_env_vars
  labels                  = local.common_labels
  cpu                     = var.cloud_run_cpu
  memory                  = var.cloud_run_memory
  concurrency             = var.cloud_run_concurrency
  min_instances           = var.cloud_run_min_instances
  max_instances           = var.cloud_run_max_instances
  timeout_seconds         = var.cloud_run_timeout_seconds
  allow_unauthenticated   = var.allow_unauthenticated

  depends_on = [
    module.project_services,
    module.bigquery,
    module.secrets,
    google_project_iam_member.runtime_bigquery_job_user,
    google_bigquery_dataset_iam_member.runtime_core_viewer,
    google_bigquery_dataset_iam_member.runtime_events_editor,
    google_bigquery_dataset_iam_member.runtime_analytics_viewer,
    google_secret_manager_secret_iam_member.runtime_secret_access,
  ]
}
