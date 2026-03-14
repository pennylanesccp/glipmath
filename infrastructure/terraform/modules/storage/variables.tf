variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "location" {
  description = "Bucket location."
  type        = string
}

variable "bucket_name" {
  description = "Name of the bucket."
  type        = string
}

variable "force_destroy" {
  description = "Allow Terraform to delete bucket contents."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels applied to the bucket."
  type        = map(string)
  default     = {}
}
