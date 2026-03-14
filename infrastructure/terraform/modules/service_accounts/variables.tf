variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "runtime_account_id" {
  description = "Account ID for the Cloud Run runtime service account."
  type        = string
}

variable "runtime_display_name" {
  description = "Display name for the runtime service account."
  type        = string
}

variable "deploy_account_id" {
  description = "Optional deploy service account ID."
  type        = string
}

variable "deploy_display_name" {
  description = "Display name for the optional deploy service account."
  type        = string
}

variable "create_deploy_service_account" {
  description = "Whether to create an extra deploy service account."
  type        = bool
}
