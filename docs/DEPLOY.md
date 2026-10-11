# Deploying

Two services: the API on Render, the web app on Vercel. Both redeploy on every push to `main`.
Deploy the API first, because the web app needs its address.

A person has to create the two accounts and connect GitHub. Everything else is in the repo.

## 1. API on Render

1. Sign in at render.com with GitHub and give Render access to this repository.
2. **New > Blueprint**, choose the repository. Render reads `render.yaml` and proposes one
   service, `sentifi-api`.
3. When asked for `CORS_ORIGINS`, enter a placeholder such as `http://localhost:3000`. You set
   the real value in step 3.
4. Create it and wait for the first deploy.
5. Open `https://<your-service>.onrender.com/api/health`. It should return `"status": "ok"`
   and `"is_demo_data": false`.

The image is built from `api/Dockerfile` with the repo root as context, so it contains the API,
the contract schemas and `data/artifacts`. It serves the artifacts that were on `main` when it
was built.

## 2. Web app on Vercel

1. Sign in at vercel.com with GitHub and import this repository.
2. Set **Root Directory** to `web`. Vercel detects Next.js.
3. Add an environment variable: `NEXT_PUBLIC_API_URL` = the Render URL from step 1, with no
   trailing slash, for example `https://sentifi-api.onrender.com`.
4. Deploy. Note the URL Vercel gives you.

## 3. Let the web app call the API

1. In Render, open `sentifi-api` > **Environment** and set `CORS_ORIGINS` to the Vercel URL,
   for example `https://sentifi.vercel.app`. Several origins are comma-separated.
2. Save. Render redeploys.
3. Open the Vercel URL. The landing page should show a live spectrum, with no "Can't reach the
   SentiFi API" card.

`NEXT_PUBLIC_API_URL` is baked in at build time. If the API address changes, change the variable
in Vercel and redeploy.

## Things to know

| Topic | What happens |
|---|---|
| Cold starts | Render's free plan stops the service when idle. The first request afterwards can take up to a minute. Open the site a few minutes before a demo. |
| Alert sign-ups | Stored in SQLite at `/tmp/alerts.db` inside the container. They are lost on every redeploy and restart. Fine for a demo, not for real users. |
| New data | Artifacts are baked into the image. New pipeline output goes live when it is merged to `main` and Render redeploys. |
| Preview URLs | Vercel gives every pull request its own URL. Those are not in `CORS_ORIGINS`, so previews cannot reach the API unless you add them. |
| Secrets | The base app needs none. The optional explainer needs `ANTHROPIC_API_KEY`, set in Render only. It must never be a `NEXT_PUBLIC_` variable. |

## Run the image locally

```bash
docker build -f api/Dockerfile -t sentifi-api .
```

```bash
docker run --rm -p 8000:8000 -e CORS_ORIGINS=http://localhost:3000 sentifi-api
```
