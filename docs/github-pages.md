---
layout: default
title: GitHub Pages
permalink: /github-pages.html
---

## Publish this repo’s docs on GitHub Pages

Use the **`docs/`** folder at the **root of this backend repository**.

1. **Settings** → **Pages** → Deploy from branch **main**, folder **`/docs`**.
2. In **`docs/_config.yml`**, keep **`url`**, **`baseurl`**, **`canonical_docs_url`**, and **`github_repo`** aligned with your real project URL, for example:

```yaml
baseurl: "/ai_receptionist_backend"
url: "https://mmansoornano.github.io"
canonical_docs_url: "https://mmansoornano.github.io/ai_receptionist_backend"
github_repo: mmansoornano/ai_receptionist_backend
```

Nav and cards use **`canonical_docs_url`** so links match **`https://<user>.github.io/<repo>/…`**. **`relative_url`** is still used for **CSS** under **`/assets/`**, so **`baseurl`** must stay correct.

[← Home]({{ site.canonical_docs_url }}/)
