---
title: Service ownership
level: 1
weight: 50
control_code: SDLC-CTRL-0011
tldr: All services running in our environments have registered ownership
rationale: In a diverse software landscape it is essential everyone knows who
  is responsible for maintaince and support
areas: 
 - process
---
# {{% param "title" %}}
{{< area_head >}}

## Background

In any governance system, risks are managed by controls. But humans are ultimately responsible.In this context there are many reasons to keep a register of service ownership in diverse software
landscapes:

* **Knowlege**: Who knows how this is supposed to work?  How can I get help with this system?
* **Incident**: Alerts are firing for a service, who do I contact?  What has changed lately?
* **Audit**: who is reponsible that the SDLC is followed for this service?

<figure class="feature-figure">
  <img src="/assets/secrets-management.svg" alt="Service ownership">
  <figcaption>Service ownership</figcaption>
</figure>

## How we implement this control

At this stage, we have a relatively simple system and a single tech team, so recording services in our application inventory is sufficient to meet this need.

