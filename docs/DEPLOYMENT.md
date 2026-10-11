# Deployment Guide

Deploys the Van Udyan Biodiversity Platform to the public internet so RSWF staff and the public
can use it from any device. **Total cost: ₹0.** Total time: about 30–45 minutes end-to-end.

Stack:

| Role | Service | Why |
| :--- | :--- | :--- |
| Database | **Supabase** (free) | PostgreSQL + PostGIS out of the box, no card required |
| Photo storage | **Supabase Storage** (free, 1 GB) | Photos survive backend redeploys |
| Backend API | **Render Web Service** (free) | Docker, HTTPS, sleeps when idle |
| Dashboard | **Render Static Site** (free) | Fast global CDN, never sleeps |

Free-tier caveat: the backend takes ~30 seconds to wake up after 15 minutes of no traffic.
Perfectly fine for occasional field use; upgrade to Render Starter ($7/month) if you need
always-on with a persistent disk.

---

## Prerequisites

1. A **GitHub account**. Push this repository to a repo of your own first:
   ```bash
   git init
   git add .
   git commit -m "Initial Van Udyan platform"
   git remote add origin https://github.com/<your-username>/van-udyan.git
   git push -u origin main
   ```
2. A **Pl@ntNet API key**. Register at [my.plantnet.org](https://my.plantnet.org/) and copy
   your developer key (free, 500 identifications/day).

---

## Step 1 — Supabase project (database + photo storage)

1. Create a free account at [supabase.com](https://supabase.com/) and click **New Project**.
   - **Region:** Mumbai (ap-south-1), closest to Pune.
   - **Database password:** generate a strong one and save it in your password manager.
2. Wait ~2 minutes for the project to be provisioned.
3. Go to **Project Settings → Database → Connection string → URI** and copy the connection
   string. It looks like:
   ```
   postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
   ```
   Save this as your `DATABASE_URL`.
4. Open the **SQL Editor** and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
5. Go to **Storage → Create a new bucket**:
   - **Name:** `van-udyan-photos`
   - **Public bucket:** ✅ yes (photos need to be viewable in the dashboard without a token).
6. Go to **Project Settings → API** and copy two values:
   - **Project URL** → save as `SUPABASE_URL`
   - **service_role secret** (⚠️ not the anon key) → save as `SUPABASE_SERVICE_KEY`

---

## Step 2 — Seed Supabase with your current data

From the project folder on your local machine (with the backend virtual environment active):

```bash
# 1. Point the local .env at the cloud database and storage
# Edit backend/.env to use the Supabase DATABASE_URL + the two Supabase values from Step 1
```

Your `backend/.env` should contain:
```env
DATABASE_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
PLANTNET_API_KEY=<your plantnet key>
PLANTNET_PROJECT=k-indian-subcontinent
NGO_ADMIN_PASSWORD=<a strong password of your choice>
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service_role secret>
SUPABASE_BUCKET=van-udyan-photos
# Leave ENABLE_STATE_SYNC off for your local .env — the migration script turns it on itself.
```

Then run the one-time migration:
```bash
backend\venv\Scripts\python.exe scripts\deploy_initial_data.py
```

This:
1. Creates the PostGIS schema and loads the boundary + zones + 227 iNaturalist records.
2. Uploads every photo in `data/uploads/` to the Supabase bucket.
3. Pushes NGO observations, planted plants and visit history into Supabase.

> **After this finishes, your local backend will use the cloud database and cloud photos too.**
> If you want to go back to a local-only setup, remove the Supabase lines from `backend/.env`.

---

## Step 3 — Deploy to Render (one click)

1. Create a free account at [render.com](https://render.com/) and connect your GitHub.
2. Click **New +** → **Blueprint** and pick the repo you pushed in the prerequisites.
   Render reads [`render.yaml`](../render.yaml) and creates two services:
   - `van-udyan-backend` (Docker web service, free tier)
   - `van-udyan-dashboard` (static site, free tier)
3. Render will prompt you for the secrets it couldn't guess. Fill in:
   - **Backend `DATABASE_URL`** — the Supabase URL from Step 1.
   - **Backend `PLANTNET_API_KEY`** — your Pl@ntNet key.
   - **Backend `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`** — from Step 1.
   - **Dashboard `API_BASE_URL`** — leave empty for now; you'll fill it after the backend
     deploys and gets its final URL (usually `https://van-udyan-backend.onrender.com`).
4. Click **Apply**. Render builds and deploys both services. Backend takes ~5 minutes the
   first time (building the Docker image with Tesseract). Dashboard takes under 1 minute.

### After the first deploy

1. Open the **backend** service page and copy its public URL
   (`https://van-udyan-backend-xxxx.onrender.com`).
2. Open the **dashboard** service → **Environment** → set `API_BASE_URL` to the backend URL
   and click **Save Changes**. Render redeploys the dashboard with that value baked in.
3. Open the **backend** service → **Environment** → set `CORS_ORIGINS` to the dashboard URL
   (`https://van-udyan-dashboard-xxxx.onrender.com`) so the browser can call the API.
4. Click the dashboard URL to open the live site. Everything from your local install should
   be there: 270 observations, 99 species, the map, the AI identification, uploads.

### Hand the admin password to RSWF

On the backend service page → **Environment**, Render generated a random `NGO_ADMIN_PASSWORD`
on first deploy. Click to reveal it and share it only with RSWF staff who will confirm species
or edit plantation records.

---

## What's different on the live site

| | Local | Deployed |
| :--- | :--- | :--- |
| Database | PostgreSQL on your PC | Supabase (free, 500 MB) |
| Photos | `data/uploads/` on your PC | Supabase Storage bucket |
| NGO data | `data/processed/*.json` on your PC | `app_state` table in Supabase (and local JSON copy) |
| OCR for GPS stamps | Windows OCR (fast) | Tesseract in the Docker image (slower, slightly less accurate) |
| First visit | Instant | Backend takes ~30 s to wake if it had no traffic for 15 min |
| HTTPS | No | Yes, automatic |

---

## Updating the site after the first deploy

Any `git push` to the `main` branch triggers an automatic redeploy of whichever service
changed. The deploy takes 2–5 minutes.

- Backend code change → Render rebuilds the Docker image.
- Frontend change → Render redeploys the static site (seconds).

NGO uploads and species confirmations made through the live site keep going straight into
Supabase, so redeploys don't lose anything.

---

## Monitoring and troubleshooting

- **Backend logs:** Render service page → **Logs**. Pl@ntNet errors, OCR failures and
  startup messages (including `state_sync: pulled ngo_observations, planted_plants from
  database`) appear here.
- **Database usage:** Supabase dashboard → **Database → Reports** shows row counts and
  storage used. The free plan has 500 MB; 10,000 observations fit comfortably.
- **Photo storage usage:** Supabase dashboard → **Storage → van-udyan-photos**. Free tier
  allows 1 GB; a typical geotagged phone photo is 2–6 MB, so ~200 photos per GB.
- **Admin password:** reset by changing `NGO_ADMIN_PASSWORD` on the backend service and
  redeploying.

Common issues:

| Problem | Fix |
| :--- | :--- |
| "Cannot reach the data server" | Backend is waking up (free tier). Wait 30 s and retry. |
| Dashboard shows 0 records | `API_BASE_URL` on the dashboard doesn't match the backend URL. |
| Photo upload returns 500 | `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` are wrong, or the bucket name doesn't match. |
| AI identification returns "no match" | Pl@ntNet daily quota (500/day) exceeded, or `PLANTNET_API_KEY` is wrong. |
| Printed GPS stamp not read on Linux | Tesseract isn't installed in the image (unusual — the Dockerfile installs it). Check backend logs. |

---

## Upgrading from the free tier

When RSWF uses the site regularly, two paid upgrades are worth it:

- **Render Starter ($7/month):** backend never sleeps, 1 GB persistent disk (so you can store
  photos locally instead of Supabase if you prefer).
- **Supabase Pro ($25/month):** 8 GB database, 100 GB storage, daily automated backups.
  Only needed if the project grows past a few thousand observations.

For a single custom domain, point your DNS at Render — see
[Render → Custom Domains](https://render.com/docs/custom-domains).
