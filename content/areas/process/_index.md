---
title: Agile Delivery Process
weight: 200
section: process
---

## Purpose

Car & General delivers application change through an Agile operating model that combines iterative planning with formal SDLC governance. This process exists to ensure delivery teams can respond quickly to business priorities while still maintaining traceable requirements, peer review, test evidence, release approval, and post-release learning.

## Operating cadence

The default delivery cadence is sprint based, with work flowing through the following sequence:

- Product backlog refinement
- Sprint planning and commitment
- Daily stand-up coordination
- Build, review, and test execution
- Demo or sprint review with business stakeholders
- Retrospective with tracked improvement actions

Teams may use Kanban-style flow for support or urgent work, but they are still expected to preserve the same minimum evidence, approvals, and closure checks.

## Roles and accountability

| Role | Primary accountability | Minimum evidence retained |
| --- | --- | --- |
| Product Owner | Prioritises backlog items, confirms business value, accepts completed work | Approved backlog, acceptance criteria, review notes |
| Scrum Master or Team Lead | Facilitates ceremonies, removes blockers, monitors process adherence | Sprint plan, action log, impediment tracking |
| Delivery Team | Designs, builds, tests, and documents changes | Pull requests, test results, implementation notes |
| Business Owner | Confirms delivered capability meets operational need | Demo sign-off, UAT outcome, deployment approval where required |
| Change Approvers | Review risk, timing, rollback readiness, and production impact | Approved change request, risk assessment, approval record |

## Required Agile artefacts

Every change delivered through the Agile process should be traceable to the following artefacts:

- A backlog item or user story with business context and acceptance criteria
- Linked technical tasks or subtasks for implementation work
- Code review evidence in the source control platform
- Test evidence covering functional, regression, and security validation where applicable
- A change request for releases that affect production services or shared infrastructure
- Release or deployment notes capturing implementation and rollback instructions
- Retrospective actions for material defects, incidents, or recurring process issues

## Ceremony expectations

### Backlog refinement

Backlog refinement confirms scope, dependencies, security considerations, and test approach before work enters a sprint or active delivery queue. Items that are ambiguous, unestimated, or missing acceptance criteria are not treated as ready for commitment.

### Sprint planning

Sprint planning records the work selected for the period, the delivery objective, identified dependencies, and ownership across the team. This creates the baseline against which sprint execution and audit traceability are measured.

### Daily stand-up

Daily stand-ups are used to surface blockers, sequencing risks, and unplanned work. Material delivery risks identified during stand-up must be reflected in the work item, team board, or change record the same day.

### Sprint review

Sprint reviews demonstrate completed work to stakeholders and record whether acceptance criteria were met, deferred, or rejected. Where deployment approval is separate from feature acceptance, both decisions must remain traceable.

### Retrospective

Retrospectives identify what worked, what did not, and what improvement actions will be carried into the next cycle. Actions that affect controls, templates, or delivery workflow should be incorporated into the SDLC portal and associated team procedures.

## Governance gates inside Agile delivery

Agile execution does not replace control requirements. The following gates remain mandatory:

- No work is deployed to production without appropriate peer review and test evidence.
- High-risk, customer-impacting, or infrastructure changes require formal change approval before implementation.
- Emergency fixes may be expedited, but they must receive retrospective review and documentation after restoration of service.
- Production releases must have rollback steps, implementation ownership, and validation steps documented before execution.

## Audit evidence and retention

Audit evidence for Agile delivery is retained across the backlog tool, source control platform, CI or test tooling, and the change management module in this portal. At minimum, teams should be able to demonstrate:

- who requested and prioritised the work
- what was changed and why
- who reviewed and approved it
- what testing was completed
- when it was deployed
- how issues and lessons learned were captured

## Exceptions

Where a team cannot follow the standard sprint cadence, the exception must be agreed with the delivery lead and compensated with equivalent documentation, approvals, and evidence retention.
