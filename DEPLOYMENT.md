# Guía de Despliegue en Google Cloud Platform (`DEPLOYMENT.md`)
**Modalidad 2.2: Google ADK + Cloud Run + Cloud SQL + Vertex AI + Secret Manager**

---

## 1. Arquitectura de Despliegue en GCP y Mínimo Privilegio (IAM)

El servicio se despliega en **Google Cloud Run** utilizando una cuenta de servicio dedicada (`sa-techcorp-adk-runner@techcorp-latam-prod.iam.gserviceaccount.com`) con únicamente los siguientes roles IAM de mínimo privilegio:
- `roles/aiplatform.user` — Invocación de modelos Gemini 2.5 Pro / Light en Vertex AI.
- `roles/cloudsql.client` — Conexión segura vía Cloud SQL Auth Proxy hacia PostgreSQL 16.
- `roles/secretmanager.secretAccessor` — Lectura de secretos (`JWT_SECRET_KEY`, `DATABASE_URL`, `FIN_PROVIDER_PRIMARY_API_KEY`) en tiempo de arranque.
- `roles/logging.logWriter` y `roles/monitoring.metricWriter` — Emisión de eventos estructurados y métricas de latencia/costos.

---

## 2. Comandos de Despliegue Paso a Paso en Cloud Run

```bash
# 1. Definir variables del proyecto GCP
export PROJECT_ID="techcorp-latam-prod"
export REGION="us-central1"
export SERVICE_ACCOUNT="sa-techcorp-adk-runner@${PROJECT_ID}.iam.gserviceaccount.com"

# 2. Construir y publicar imagen del Backend + ADK Runner en Artifact Registry
gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/techcorp-repo/asistente-backend:1.0.0" -f deploy/Dockerfile.backend .

# 3. Desplegar Backend en Cloud Run con Secret Manager y Cloud SQL vinculados
gcloud run deploy techcorp-asistente-backend \
  --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/techcorp-repo/asistente-backend:1.0.0" \
  --region "${REGION}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --add-cloudsql-instances "${PROJECT_ID}:${REGION}:techcorp-pg16-prod" \
  --set-secrets "JWT_SECRET_KEY=jwt-secret-key:latest,DATABASE_URL=cloudsql-db-url:latest,FIN_PROVIDER_PRIMARY_API_KEY=fin-api-primary:latest" \
  --set-env-vars "APP_ENV=production,GCP_PROJECT_ID=${PROJECT_ID},VERTEX_PRIMARY_MODEL=gemini-2.5-pro,VERTEX_LIGHT_MODEL=gemini-2.5-flash" \
  --min-instances 1 \
  --max-instances 15 \
  --cpu 2 \
  --memory 4Gi \
  --no-allow-unauthenticated
```
