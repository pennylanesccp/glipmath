variable "project_id" {
  description = "Target GCP project ID."
  type        = string
  default     = "ide-math-app"
}

variable "environment" {
  description = "Environment name used in labels and naming."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Default region for Cloud Run and regional resources."
  type        = string
  default     = "southamerica-east1"
}

variable "bigquery_location" {
  description = "BigQuery location."
  type        = string
  default     = "southamerica-east1"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "glipmath-app"
}

variable "artifact_repository_id" {
  description = "Artifact Registry repository ID."
  type        = string
  default     = "glipmath"
}

variable "runtime_service_account_id" {
  description = "Service account ID for Cloud Run runtime."
  type        = string
  default     = "glipmath-runtime"
}

variable "create_deploy_service_account" {
  description = "Whether to create a dedicated deploy service account."
  type        = bool
  default     = false
}

variable "deploy_service_account_id" {
  description = "Optional deploy service account ID."
  type        = string
  default     = "glipmath-deploy"
}

variable "seed_bucket_name" {
  description = "Bucket name for seed files and future exports."
  type        = string
  default     = "ide-math-app-dev-glipmath-seed"
}

variable "core_dataset_id" {
  description = "BigQuery dataset for core tables."
  type        = string
  default     = "glipmath_core"
}

variable "events_dataset_id" {
  description = "BigQuery dataset for append-only events."
  type        = string
  default     = "glipmath_events"
}

variable "analytics_dataset_id" {
  description = "BigQuery dataset for analytics views."
  type        = string
  default     = "glipmath_analytics"
}

variable "question_bank_table_id" {
  description = "Question bank table ID."
  type        = string
  default     = "question_bank"
}

variable "whitelist_table_id" {
  description = "Whitelist table ID."
  type        = string
  default     = "whitelist"
}

variable "answers_table_id" {
  description = "Answers table ID."
  type        = string
  default     = "answers"
}

variable "leaderboard_view_id" {
  description = "Leaderboard view ID."
  type        = string
  default     = "v_leaderboard"
}

variable "user_totals_view_id" {
  description = "User totals view ID."
  type        = string
  default     = "v_user_totals"
}

variable "user_daily_activity_view_id" {
  description = "User daily activity view ID."
  type        = string
  default     = "v_user_daily_activity"
}

variable "deploy_cloud_run" {
  description = "Whether Terraform should deploy the Cloud Run service."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Docker image URL for Cloud Run. Required when deploy_cloud_run is true."
  type        = string
  default     = ""
}

variable "cloud_run_cpu" {
  description = "CPU limit for Cloud Run."
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Memory limit for Cloud Run."
  type        = string
  default     = "512Mi"
}

variable "cloud_run_concurrency" {
  description = "Concurrency for Cloud Run."
  type        = number
  default     = 20
}

variable "cloud_run_min_instances" {
  description = "Minimum Cloud Run instances."
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum Cloud Run instances."
  type        = number
  default     = 2
}

variable "cloud_run_timeout_seconds" {
  description = "Cloud Run request timeout in seconds."
  type        = number
  default     = 300
}

variable "allow_unauthenticated" {
  description = "Allow public access to the app endpoint."
  type        = bool
  default     = true
}

variable "labels" {
  description = "Extra labels applied to resources."
  type        = map(string)
  default     = {}
}

variable "auth_cookie_secret_id" {
  description = "Secret Manager secret ID for the Streamlit cookie secret."
  type        = string
  default     = "glipmath-auth-cookie-secret"
}

variable "auth_client_id_secret_id" {
  description = "Secret Manager secret ID for the Google OIDC client ID."
  type        = string
  default     = "glipmath-auth-client-id"
}

variable "auth_client_secret_secret_id" {
  description = "Secret Manager secret ID for the Google OIDC client secret."
  type        = string
  default     = "glipmath-auth-client-secret"
}

variable "auth_redirect_uri_secret_id" {
  description = "Secret Manager secret ID for the OIDC redirect URI."
  type        = string
  default     = "glipmath-auth-redirect-uri"
}

variable "auth_server_metadata_url_secret_id" {
  description = "Secret Manager secret ID for the OIDC metadata URL."
  type        = string
  default     = "glipmath-auth-server-metadata-url"
}
