---
layout: default
title: Architecture
permalink: /architecture.html
---

## Backend overview

The **backend** is the system of record and HTTP façade for:

- **REST resources** (products, cart, orders, payments, customers, conversations) consumed by the agent’s tools and by the web app.
- **Webhooks** (e.g. Twilio) for SMS/voice entry points.
- **Optional voice** pipelines (TTS/STT) and related configuration (see `services/` and env vars in README).

## Architecture diagram

<figure class="doc-figure">
  <img src="{{ '/assets/img/backend-architecture.svg' | relative_url }}" width="920" height="400" alt="Diagram: frontend, agent, and webhooks calling Django REST, with apps and services below" loading="lazy" decoding="async" />
  <figcaption>High-level callers and Django boundary. SVG is <code>docs/assets/img/backend-architecture.svg</code> — safe to edit as vector text.</figcaption>
</figure>

## Technology stack

| Layer | Technology | Testing |
|-------|------------|---------|
| HTTP / REST | **Django** + **Django REST Framework** — viewsets, serializers, URLs | <code>python manage.py test</code>; add per-app tests under <code>apps/&lt;app&gt;/tests/</code> |
| Webhooks | **Twilio** handlers (see `apps/webhooks/` and README) | Manual or integration tests with Twilio test credentials |
| Voice | **services/** (STT/TTS, provider adapters) | Smoke paths from README; optional CI with fixtures |
| Config | **.env** + **config.py** / Django settings | Validate required vars in staging; no single bundled e2e suite yet |
| Agent bridge | **AGENT_API_URL** when the backend invokes the agent | Exercise against a running agent in a dev environment |

## Repository layout

| Path | Responsibility | Testing |
|------|----------------|---------|
| `apps/core/` | Customer, appointments, shared models | Extend with <code>TestCase</code> / pytest-django as you add coverage |
| `apps/conversations/` | Conversation tracking | Same |
| `apps/webhooks/` | Twilio and related ingress | Request factory or live webhook tests |
| `services/` | Voice, TTS compatibility layers | Integration or mocked unit tests per module |
| `utils/` | Logging, TTS text helpers | Small unit tests where logic grows |
| `auth/tests.py` | Auth app sample tests | <code>python manage.py test auth</code> |

## Agent and frontend (other repos)

- **Agent** (separate repo): LangGraph + FastAPI. This backend exposes URLs the agent calls; configure the agent with **`BACKEND_API_BASE_URL`** pointing here.
- **Frontend** (separate repo): React app using **`VITE_BACKEND_URL`** pointing here.

This backend reaches the agent when needed via **`AGENT_API_URL`** (see `.env.example`).

See [Integration]({{ site.canonical_docs_url }}/integration.html).

[← Home]({{ site.canonical_docs_url }}/)
