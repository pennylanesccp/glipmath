resource "google_bigquery_dataset" "core" {
  project                    = var.project_id
  dataset_id                 = var.core_dataset_id
  location                   = var.location
  delete_contents_on_destroy = false
  labels                     = var.labels
}

resource "google_bigquery_dataset" "events" {
  project                    = var.project_id
  dataset_id                 = var.events_dataset_id
  location                   = var.location
  delete_contents_on_destroy = false
  labels                     = var.labels
}

resource "google_bigquery_dataset" "analytics" {
  project                    = var.project_id
  dataset_id                 = var.analytics_dataset_id
  location                   = var.location
  delete_contents_on_destroy = false
  labels                     = var.labels
}

resource "google_bigquery_table" "question_bank" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.core.dataset_id
  table_id            = var.question_bank_table_id
  schema              = var.question_bank_schema
  deletion_protection = false
  labels              = var.labels
}

resource "google_bigquery_table" "user_access" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.core.dataset_id
  table_id            = var.user_access_table_id
  schema              = var.user_access_schema
  deletion_protection = false
  labels              = var.labels
}

resource "google_bigquery_table" "answers" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.events.dataset_id
  table_id            = var.answers_table_id
  schema              = var.answers_schema
  deletion_protection = false
  labels              = var.labels

  time_partitioning {
    type  = "DAY"
    field = "answered_at_utc"
  }

  clustering = ["user_email", "id_question"]
}

resource "google_bigquery_table" "user_totals_view" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = var.user_totals_view_id
  deletion_protection = false
  labels              = var.labels

  view {
    query          = var.user_totals_view_query
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.answers]
}

resource "google_bigquery_table" "user_daily_activity_view" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = var.user_daily_activity_view_id
  deletion_protection = false
  labels              = var.labels

  view {
    query          = var.user_daily_activity_view_query
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.answers]
}

resource "google_bigquery_table" "leaderboard_view" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = var.leaderboard_view_id
  deletion_protection = false
  labels              = var.labels

  view {
    query          = var.leaderboard_view_query
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.user_totals_view]
}
