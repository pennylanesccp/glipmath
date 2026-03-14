output "runtime_email" {
  description = "Runtime service account email."
  value       = google_service_account.runtime.email
}

output "deploy_email" {
  description = "Deploy service account email if created."
  value       = var.create_deploy_service_account ? google_service_account.deploy[0].email : null
}
