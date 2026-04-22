---
layout: default
title: Testing
permalink: /testing.html
---

## Where to run

Use the **backend repository root** (`AI_receptionist_backend/`) where **`manage.py`** lives. Activate your virtualenv or conda env and install **`requirements.txt`** first.

## Django test runner

| Goal | Command |
|------|---------|
| **Full project** | `python manage.py test` |
| **One app** | `python manage.py test auth` |
| **Verbose** | `python manage.py test -v 2` |

Today the repo ships a minimal example at **`auth/tests.py`**. Add **`tests.py`** or **`tests/`** packages under each **`apps/<name>/`** module as you grow coverage (see Django’s [Testing in Django](https://docs.djangoproject.com/en/stable/topics/testing/) documentation).

## What to test locally

- **Models and serializers** — unit tests with `TestCase` and API factories.
- **REST viewsets** — `APIClient`, authenticated requests, and permission cases.
- **Webhooks** — POST shapes that match Twilio (or your gateway); use test credentials and **`DEBUG`**-only routes where documented in **README.md**.

## End-to-end with the agent

The **agent** repo has **`tests/test_backend_integration.py`**, which calls your live Django base URL (**`BACKEND_API_BASE_URL`** in the agent’s **`.env`**). Bring this backend up (`runserver` or your deploy URL), then run that test module from the **agent** checkout with **`-m integration`**.

LLM **scenario** runs (boxed **user input / router / time / agent output**, quiet logs unless a test fails) are documented on the **agent** repository’s GitHub Pages **Testing** page (`testing.html` in that repo’s `docs/` site).

## Related docs

- [Architecture]({{ site.canonical_docs_url }}/architecture.html) — repository layout and testing column.
- Root **README.md** — setup, migrations, and runserver.
