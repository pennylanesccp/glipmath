output "core_dataset_id" {
  description = "Core dataset ID."
  value       = google_bigquery_dataset.core.dataset_id
}

output "events_dataset_id" {
  description = "Events dataset ID."
  value       = google_bigquery_dataset.events.dataset_id
}

output "analytics_dataset_id" {
  description = "Analytics dataset ID."
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "question_bank_table_id" {
  description = "Question bank table ID."
  value       = google_bigquery_table.question_bank.table_id
}

output "user_access_table_id" {
  description = "User access table ID."
  value       = google_bigquery_table.user_access.table_id
}

output "answers_table_id" {
  description = "Answers table ID."
  value       = google_bigquery_table.answers.table_id
}

output "leaderboard_view_id" {
  description = "Leaderboard view ID."
  value       = google_bigquery_table.leaderboard_view.table_id
}
