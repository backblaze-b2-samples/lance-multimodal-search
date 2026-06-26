# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_REGION` | Your B2 region (e.g., `us-west-004`); the API derives the S3-compatible endpoint |
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_PUBLIC_URL_BASE` | Optional public base URL for direct object links |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

Rolling migration note: while deploying this B2 standards change over an older
API revision, keep `B2_ENDPOINT=https://s3.<B2_REGION>.backblazeb2.com` in the
production environment until every old instance is drained. New code derives the
endpoint from `B2_REGION` and tolerates `B2_ENDPOINT` for one release, but old
instances need the explicit value to avoid falling back to their previous
default endpoint. `B2_PUBLIC_URL` is also tolerated for one release; use
`B2_PUBLIC_URL_BASE` for new configuration.

> The CLIP model and `torch` are CPU-only but sizeable; size the API service accordingly. The model downloads once on first use.

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
