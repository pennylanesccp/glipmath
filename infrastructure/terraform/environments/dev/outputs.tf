output "runtime_service_account_email" {
  description = "Runtime service account email."
  value       = module.service_accounts.runtime_email
}

output "artifact_repository_url" {
  description = "Artifact Registry Docker repository URL."
  value       = module.artifact_registry.repository_url
}

output "seed_bucket_name" {
  description = "Bucket for seed files and exports."
  value       = module.storage.bucket_name
}

output "core_dataset_id" {
  description = "Core dataset ID."
  value       = module.bigquery.core_dataset_id
}

output "events_dataset_id" {
  description = "Events dataset ID."
  value       = module.bigquery.events_dataset_id
}

output "analytics_dataset_id" {
  description = "Analytics dataset ID."
  value       = module.bigquery.analytics_dataset_id
}

output "secret_ids" {
  description = "Created Secret Manager secret IDs."
  value       = module.secrets.secret_names
}

output "cloud_run_url" {
  description = "Cloud Run service URL if deployed."
  value       = var.deploy_cloud_run ? module.cloud_run[0].service_url : null
}
