# Deploy Neta-Resume — beginner walkthrough

A click-by-click guide to put the site live. `docs/DEPLOYMENT.md` is the terse reference; **this** is the
hand-held version. No prior cloud experience assumed.

## The plan (and why)

You have three pieces to host: the **database**, the **API**, and the **website**. We use your **AWS
credits** for the two compute pieces and a **free** managed database — because the single hardest part of
an all-AWS setup for a beginner is the database networking (VPC / security groups so the API can reach
RDS). A managed Postgres with a public, password-protected endpoint sidesteps all of that.

| Piece | Where | Why | Cost |
|------|-------|-----|------|
| **Database** | **Neon** (neon.tech) free tier | Public SSL endpoint → the API reaches it with zero networking setup. Free forever at this size. | **$0** |
| **API** (FastAPI) | **AWS App Runner** | Deploys straight from your GitHub repo, builds with `pip`, autoscales. No Docker needed. | credits (~$5–25/mo equiv.) |
| **Website** (Next.js) | **AWS Amplify Hosting** | Native Next.js support, builds from GitHub on every push. | credits (mostly free tier) |
| **Data refresh** | **GitHub Actions** (already in the repo) | Runs the ingestion pipelines on a schedule → writes to Neon. | $0 |

> Prefer keeping the database in AWS too (to spend credits / keep one bill)? See **Appendix B** for the
> RDS variant. Everything else stays the same.

```
 Browser ──▶ Amplify (web) ──▶ App Runner (api) ──▶ Neon (Postgres)
                                                       ▲
                          GitHub Actions (ingestion) ──┘
```

---

## Stage 0 — One-time prerequisites (~10 min)

1. **AWS account** with your credits applied (Billing → Credits shows them).
2. **GitHub**: the repo is already at `github.com/SahilSawant/neta-resume` and pushed. Good.
3. **Postgres client tools locally** (for the data load): `psql` and `pg_dump`. On macOS:
   `brew install libpq && brew link --force libpq` (or `brew install postgresql@16`). Check:
   `psql --version`.
4. Your **local database is running** with the data (it is — 784 legislators).

You do **not** need Docker for this path.

---

## Stage 1 — Create the database (Neon) (~5 min)

1. Go to **neon.tech** → sign up (GitHub login is fine) → **Create project**.
2. Name it `neta-resume`, region closest to you, Postgres 16. Create.
3. On the project dashboard, find **Connection string** (a "Connection Details" panel). Copy the
   **psql / URI** string. It looks like:
   ```
   postgresql://neta_owner:XXXXXXXX@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. **Save this string somewhere private** (a password manager). This is your `NETA_DATABASE_URL`.
   - Note: Neon's default database is `neondb`. That's fine — the app doesn't care about the name.
   - The app uses the `+psycopg` driver. For the **app's** env var, prefix the scheme:
     `postgresql+psycopg://...` (same string, just `postgresql+psycopg://` at the front). For `psql`/the
     load script below, use it **without** `+psycopg` (plain `postgresql://`).

---

## Stage 2 — Load the schema + your data into Neon (~3 min)

From the repo root, run the helper (use the **plain** `postgresql://` form here):

```bash
TARGET_DSN="postgresql://neta_owner:XXXX@ep-...neon.tech/neondb?sslmode=require" \
  ./scripts/load_remote_db.sh
```

It copies your local database (schema + all 784 legislators + attendance) into Neon and prints a row
count to confirm. If it prints `people | 784`, you're done with the database.

---

## Stage 3 — Deploy the API (AWS App Runner) (~10 min)

1. AWS Console → search **App Runner** → **Create service**.
2. **Source**: choose **Source code repository** → **Add new** → connect your **GitHub** (authorize AWS
   Connector for GitHub) → pick the `neta-resume` repo, branch `main`.
3. **Deployment trigger**: Automatic (redeploys when you push).
4. **Configure build**:
   - **Configuration file**: choose **Configure all settings here** (not a config file).
   - **Runtime**: **Python 3** (pick 3.12 if offered, else 3.11 — the code runs on both).
   - **Source directory**: `api`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn neta_api.main:app --host 0.0.0.0 --port 8000`
   - **Port**: `8000`
5. **Service settings**:
   - **Environment variables** — add:
     - `NETA_DATABASE_URL` = your Neon string **with** `postgresql+psycopg://` prefix and
       `?sslmode=require` at the end.
     - `NETA_ALLOWED_ORIGINS` = `http://localhost:3000` (placeholder — we fix this in Stage 5).
   - CPU/memory: smallest (0.25 vCPU / 0.5 GB) is plenty.
   - **Health check**: Path `/health` (Protocol HTTP). This is why the API has a `/health` route.
6. **Create & deploy**. Wait ~5 min for "Running". Copy the **Default domain** (e.g.
   `https://abcd1234.us-east-2.awsapprunner.com`) — this is your **API URL**.
7. Test it: open `<API URL>/health` in a browser → `{"status":"ok"}`. And `<API URL>/persons?limit=3`
   should return JSON.

---

## Stage 4 — Deploy the website (AWS Amplify) (~10 min)

1. AWS Console → search **Amplify** → **Create new app** → **Host web app** → **GitHub** → authorize →
   pick `neta-resume`, branch `main`.
2. **App settings / monorepo**: set the **app root / base directory** to `web` (the frontend lives in
   `web/`). Amplify should auto-detect **Next.js**.
3. **Environment variables** — add:
   - `NETA_API_BASE` = your **API URL** from Stage 3 (e.g. `https://abcd1234...awsapprunner.com`,
     no trailing slash).
4. **Save and deploy**. Wait ~5 min. Amplify gives you a URL like
   `https://main.d1234abcd.amplifyapp.com` — this is your **website URL**.
5. Open it. The pages load but **photos/data may fail** until we fix CORS — next stage.

---

## Stage 5 — Connect the two (CORS) (~3 min)

The API only answers browsers from origins you allow. Right now that's still localhost.

1. App Runner → your service → **Configuration** → **Edit** → **Environment variables**.
2. Set `NETA_ALLOWED_ORIGINS` = your **website URL** from Stage 4 (e.g.
   `https://main.d1234abcd.amplifyapp.com`). You can list several comma-separated.
3. **Save** → App Runner redeploys (~3 min).
4. Reload the website — the directory, photos, and profiles should all work now.

---

## Stage 6 — Turn on scheduled data refresh (~2 min)

Give GitHub Actions the database so the ingestion pipelines can refresh data on schedule.

```bash
gh secret set NETA_DATABASE_URL --repo SahilSawant/neta-resume
# paste the Neon string WITH +psycopg, e.g. postgresql+psycopg://neta_owner:XXXX@ep-...neon.tech/neondb?sslmode=require
```

(Run it yourself so the password never lands in chat.) The `ingest.yml` workflow's weekly cron will now
update Neon; the site reflects it on the next page load.

---

## Stage 7 — Verify end-to-end

- `<API URL>/health` → ok; `<API URL>/persons?limit=3` → JSON with `current_attendance_pct`.
- Website loads, directory shows photos + assets + attendance, a profile opens with all tabs.
- Push a trivial commit → Amplify rebuilds the web and App Runner redeploys the API automatically.

You're live. 🎉

---

## Appendix A — What it costs

- **Neon**: free at this size.
- **App Runner**: bills for the running instance (~$5–25/mo equivalent) — covered by credits. Pause or
  delete the service to stop charges.
- **Amplify**: build minutes + hosting; small sites are within free tier — covered by credits.
- **GitHub Actions**: free.

So with credits applied: effectively **$0 out of pocket**, and ~$0 even without credits except the API
instance.

## Appendix B — All-AWS variant (RDS instead of Neon)

If you'd rather keep the database in AWS: create an **RDS PostgreSQL** `db.t4g.micro` (free tier 12
months), **Publicly accessible = Yes**, and a security group inbound rule allowing Postgres (5432) — for
the data load, from your IP; for the API, from App Runner (simplest: allow your VPC / or keep it public
with a strong password). Then run Stage 2's `load_remote_db.sh` against the RDS endpoint and use the RDS
connection string everywhere Neon's was used. The rest of the walkthrough is identical. See
`docs/DEPLOYMENT.md` for the read-only DB role and the cleaner VPC-connector setup once you're comfortable.

## Appendix C — Teardown (stop all charges)

- App Runner → delete the service.
- Amplify → delete the app.
- Neon → delete the project (or leave it, it's free).
- RDS (if used) → delete the instance (final snapshot optional).

## Appendix D — Container alternative (if you ever want Docker)

The repo also ships `api/Dockerfile`, `web/Dockerfile`, and a full-stack `docker-compose.yml`. If you
later install Docker, you can build the API image and deploy it to App Runner **from ECR** instead of the
source-build path above, or run the whole stack locally with `docker compose up`. Not needed for this
walkthrough.
