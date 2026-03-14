variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "location" {
  description = "BigQuery location."
  type        = string
}

variable "core_dataset_id" {
  description = "Dataset ID for core business tables."
  type        = string
}

variable "events_dataset_id" {
  description = "Dataset ID for append-only event tables."
  type        = string
}

variable "analytics_dataset_id" {
  description = "Dataset ID for analytics views."
  type        = string
}

variable "question_bank_table_id" {
  description = "Question bank table ID."
  type        = string
}

variable "whitelist_table_id" {
  description = "Whitelist table ID."
  type        = string
}

variable "answers_table_id" {
  description = "Answers table ID."
  type        = string
}

variable "leaderboard_view_id" {
  description = "Leaderboard view ID."
  type        = string
}

variable "user_totals_view_id" {
  description = "User totals view ID."
  type        = string
}

variable "user_daily_activity_view_id" {
  description = "User daily activity view ID."
  type        = string
}

variable "question_bank_schema" {
  description = "JSON schema for the question bank table."
  type        = string
}

variable "whitelist_schema" {
  description = "JSON schema for the whitelist table."
  type        = string
}

variable "answers_schema" {
  description = "JSON schema for the answers table."
  type        = string
}

variable "leaderboard_view_query" {
  description = "SQL query for the leaderboard view."
  type        = string
}

variable "user_totals_view_query" {
  description = "SQL query for the user totals view."
  type        = string
}

variable "user_daily_activity_view_query" {
  description = "SQL query for the user daily activity view."
  type        = string
}

variable "labels" {
  description = "Labels applied to datasets and tables."
  type        = map(string)
  default     = {}
}
