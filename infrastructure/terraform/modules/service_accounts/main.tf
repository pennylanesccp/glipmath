resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_account_id
  display_name = var.runtime_display_name
}

resource "google_service_account" "deploy" {
  count = var.create_deploy_service_account ? 1 : 0

  project      = var.project_id
  account_id   = var.deploy_account_id
  display_name = var.deploy_display_name
}
