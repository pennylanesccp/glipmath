output "bucket_name" {
  description = "Seed and exports bucket name."
  value       = google_storage_bucket.this.name
}
