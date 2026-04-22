---
layout: default
title: Home
---

## Backend service overview

This **repository** is the **Django REST API**: catalog, cart, customers, payments, conversations, webhooks (e.g. Twilio), and optional voice/TTS integration. It is deployed **independently** of the agent and frontend repos.

<div class="doc-cards">
  <a class="doc-card" href="{{ site.canonical_docs_url }}/architecture.html"><strong>Architecture</strong><span>What this service does and how it fits in the stack</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/integration.html"><strong>Integration</strong><span>Agent, frontend, and environment variables</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/vendored-dia2.html"><strong>Vendored Dia2</strong><span>Voice source tree and clone implications</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/dependencies.html"><strong>Dependencies</strong><span>Python stack and reproducible installs</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/testing.html"><strong>Testing</strong><span>Django test runner and agent integration</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/github-pages.html"><strong>GitHub Pages</strong><span>How this documentation site is published</span></a>
</div>

## Runbook

See the repository root **`README.md`** for install, **`.env`**, migrations, and **`runserver`**.
