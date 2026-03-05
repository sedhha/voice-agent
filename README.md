## Local run

Run locally with Docker:

```bash
docker compose up --build
```

## IaC deploy pipeline (GCP Cloud Run)

This repo now includes a simple Terraform + GitHub Actions deployment pipeline:

- Terraform files: `infra/`
- CI/CD workflow: `.github/workflows/deploy.yml`
- Deploy target: Cloud Run (`us-central1`)
- Container registry: Artifact Registry repo `voice-agent`
- Runtime `CC_API_URL`: `https://krep.vercel/app`

### Required GitHub repository secrets

- `GCP_PROJECT_ID`: GCP project ID
- `GCP_SA_KEY`: JSON key for a service account with permissions for:
  - Cloud Run Admin
  - Artifact Registry Admin
  - Service Account User
  - Storage Admin (for Terraform state bucket)
  - Service Usage Admin (for enabling APIs)
- `GOOGLE_API_KEY`: Gemini API key passed to the app runtime

### Deploy

- Push to `main`, or
- Run `Deploy Voice Agent` manually from GitHub Actions

The workflow will:

1. Ensure a Terraform state bucket exists.
2. Bootstrap infra (APIs, Artifact Registry, Cloud Run service).
3. Build and push the app image.
4. Re-apply Terraform with the new image tag.
