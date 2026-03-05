variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "compliance-copilot-voice-agent"
}

variable "artifact_repository" {
  description = "Artifact Registry repository ID."
  type        = string
  default     = "voice-agent"
}

variable "container_image" {
  description = "Container image URI deployed to Cloud Run."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "google_api_key" {
  description = "Gemini/Google API key passed to the app runtime."
  type        = string
  sensitive   = true
}

variable "cc_api_url" {
  description = "Compliance Copilot API base URL."
  type        = string
  default     = "https://krep.vercel/app"
}

variable "allow_unauthenticated" {
  description = "Allow public unauthenticated access to Cloud Run."
  type        = bool
  default     = true
}
