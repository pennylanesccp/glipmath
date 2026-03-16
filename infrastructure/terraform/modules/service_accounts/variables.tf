variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "runtime_account_id" {
  description = "Account ID for the Streamlit app runtime service account."
  type        = string
}

variable "runtime_display_name" {
  description = "Display name for the runtime service account."
  type        = string
}
