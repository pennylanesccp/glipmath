variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Cloud Run region."
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
}

variable "container_image" {
  description = "Container image URL."
  type        = string
}

variable "service_account_email" {
  description = "Runtime service account email."
  type        = string
}

variable "env_vars" {
  description = "Plain environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Mapping of env var names to Secret Manager secret IDs."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Labels applied to the Cloud Run service."
  type        = map(string)
  default     = {}
}

variable "cpu" {
  description = "CPU limit for the container."
  type        = string
}

variable "memory" {
  description = "Memory limit for the container."
  type        = string
}

variable "concurrency" {
  description = "Maximum concurrent requests per instance."
  type        = number
}

variable "min_instances" {
  description = "Minimum instance count."
  type        = number
}

variable "max_instances" {
  description = "Maximum instance count."
  type        = number
}

variable "timeout_seconds" {
  description = "Request timeout in seconds."
  type        = number
}

variable "container_port" {
  description = "Container port exposed by Streamlit."
  type        = number
  default     = 8080
}

variable "ingress" {
  description = "Cloud Run ingress setting."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "allow_unauthenticated" {
  description = "Whether the service is publicly invokable."
  type        = bool
  default     = true
}
