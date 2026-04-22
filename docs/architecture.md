---
layout: default
title: Architecture
permalink: /architecture.html
---

# What this repository does

## Role

The **backend** is the system of record and HTTP façade for:

- **REST resources** (products, cart, orders, payments, customers, conversations) consumed by the agent’s tools and by the web app.
- **Webhooks** (e.g. Twilio) for SMS/voice entry points.
- **Optional voice** pipelines (TTS/STT) and related configuration (see `services/` and env vars in README).

## Agent and frontend (other repos)

- **Agent** (separate repo): LangGraph + FastAPI. This backend exposes URLs the agent calls; you configure the agent with **`BACKEND_API_BASE_URL`** pointing here.
- **Frontend** (separate repo): React app using **`VITE_BACKEND_URL`** pointing here.

This backend reaches the agent when needed via **`AGENT_API_URL`** (see `.env.example`).

[← Home]({{ "/" | relative_url }})
