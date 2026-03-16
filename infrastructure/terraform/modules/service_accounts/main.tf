resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_account_id
  display_name = var.runtime_display_name
}
