output "runtime_service_account_email" {
  description = "Runtime service account email."
  value       = module.service_accounts.runtime_email
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

output "question_bank_table_id" {
  description = "Question bank table ID."
  value       = module.bigquery.question_bank_table_id
}

output "user_access_table_id" {
  description = "User access table ID."
  value       = module.bigquery.user_access_table_id
}

output "answers_table_id" {
  description = "Answers table ID."
  value       = module.bigquery.answers_table_id
}

output "leaderboard_view_id" {
  description = "Leaderboard view ID."
  value       = module.bigquery.leaderboard_view_id
}
