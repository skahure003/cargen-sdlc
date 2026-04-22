---
title: Deployment Controls
level: 1
weight: 20
control_code: SDLC-CTRL-0013
tldr: Deployments controls are enforced in the pipeline and environments
rationale: Ensuring only compliant, approved software deployments are made to production
areas: 
 - change
---
# {{% param "title" %}}
{{< area_head >}}

## Background

We use deployment controls to automatically ensure we only deploy software that
has gone through our Software Development Lifecycle.  This can be implemented as
a gate in the pipeline, or as an admission controller in the environment (ideally
both).

<figure class="feature-figure">
  <img src="/assets/deployment-controls.svg" alt="Deployment Controls">
  <figcaption>Deployment Controls</figcaption>
</figure>

## How we implement this control

* We perform application security tests before deployment to confirm the release is safe to promote
