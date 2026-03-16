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
  description = "Default Google provider region."
  type        = string
  default     = "southamerica-east1"
}

variable "bigquery_location" {
  description = "BigQuery location."
  type        = string
  default     = "southamerica-east1"
}

variable "runtime_service_account_id" {
  description = "Service account ID used by the Streamlit app to access BigQuery."
  type        = string
  default     = "glipmath-streamlit"
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

variable "labels" {
  description = "Extra labels applied to resources."
  type        = map(string)
  default     = {}
}
