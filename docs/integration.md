---
layout: default
title: Integration
permalink: /integration.html
---

# Integration (separate repos)

## Agent repo

1. Deploy the agent service; note its base URL (e.g. `https://agent.example.com`).
2. In **this** backend repo, set in `.env`:

   `AGENT_API_URL=https://agent.example.com`

3. In the **agent** repo, set:

   `BACKEND_API_BASE_URL=https://api.example.com`

   (this backend’s public URL)

## Frontend repo

1. Deploy the SPA.
2. Set **`VITE_BACKEND_URL`** in the frontend build to this backend’s public URL.

CORS on **this** Django app must allow the frontend origin in production.

[← Home]({{ site.canonical_docs_url }}/)
