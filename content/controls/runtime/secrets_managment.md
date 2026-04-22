---
title: Secrets Management
level: 1
weight: 30
control_code: SDLC-CTRL-0014
tldr: Build and runtime secrets are stored securely and documented appropriately
rationale: Leaked secrets such as api keys, cryptography keys, identity tokens
  are a common attack scenario.
areas:
  - change
---

# {{% param "title" %}}

{{< area_head >}}

## Background

Secrets must be stored carefully so they do not leak into the wrong hands.
We keep application secrets in `.env` files and control how they are shared and updated.
Our GitHub repositories are checked regularly for leaked secrets so issues can be found quickly.

<figure class="feature-figure">
  <img src="/assets/secrets-management.svg" alt="Secrets Management">
  <figcaption>Secrets Management</figcaption>
</figure>

## How we implement this control

- Secrets are stored in `.env` files and are not committed to GitHub.
- Access to secrets is limited to the people and systems that need them.
- GitHub repositories are checked regularly for leaked secrets and accidental exposure.
- If a secret is exposed, it must be rotated and replaced promptly.
