---
title: Change Records
level: 1
weight: 10
control_code: SDLC-CTRL-0012
tldr: All systems and services maintain a record of changes
rationale: To meet our change management requirements, all changes to production systems are recorded permanently
areas: 
 - change
---

# {{% param "title" %}}
{{< area_head >}}

## Background

The deployment steps in our pipelines automatically log all deployments, and we can also control that we only deploy software that is approved in the {{% param "csor"  %}} audit trail.

<figure class="feature-figure">
  <img src="/assets/change-records.svg" alt="Change records">
  <figcaption>Change records</figcaption>
</figure>

## How we implement this control

* Production changes are managed through GitHub, where all code changes are tracked using version control.
* Each change is recorded through commits, pull requests, and merge history, which show what was changed, who made the change, and when it was approved and merged.
