# Testing Guide

This guide covers how to validate the Car & General SDLC portal locally, with emphasis on the `change_management` workflow.

## Scope

Current automated coverage exists mainly for:

- Django smoke tests
- change request creation
- object-level access checks
- single-step approver workflow
- risk assessment persistence without extra approval routing
- lifecycle transition gates
- demo user seeding

Current manual validation is still important for:

- page layout and styling
- login/logout flow
- template downloads
- SDLC policy rendering
- end-to-end multi-user workflow behavior

## Prerequisites

From [README.md](D:/code-agent-evaluation/cargen-sdlc/README.md):

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Apply migrations:

```powershell
python manage.py migrate
```

4. Seed local demo users if you want to test the workflow manually:

```powershell
python manage.py seed_demo_users
```

5. Start the app:

```powershell
python manage.py runserver
```

## Environment Notes

- Local database: SQLite at `db.sqlite3`
- Local static files work best with `DEBUG=1`
- Default local host values are read from [settings.py](D:/code-agent-evaluation/cargen-sdlc/config/settings.py)
- Test runs use a separate temporary test database

## Automated Tests

Run the current app test suite:

```powershell
python manage.py test change_management
```

Run all Django tests in the repository:

```powershell
python manage.py test
```

Useful validation command:

```powershell
python manage.py check
```

## Current Automated Coverage

The current suite in [tests.py](D:/code-agent-evaluation/cargen-sdlc/change_management/tests.py) verifies:

- dashboard and policy page load
- login page renders
- section pages do not duplicate top-level headings
- requesters can create a change request
- requesters cannot attach evidence to another requester's change
- requesters only see their own requests
- unrelated users cannot view approver-owned requests
- high-risk assessments do not add extra approval steps
- scheduling requires a completed risk assessment
- implementation requires a planned window
- closure requires results and evidence
- demo-user seeding command works
- approver can approve or reject a request

## Demo Users For Manual Testing

After running `python manage.py seed_demo_users`, use these local accounts:

- `requester_demo` / `Requester123!`
- `approver_demo` / `Approver123!`
- `implementer_demo` / `Implementer123!`
- `auditor_demo` / `Auditor123!`
- `sdlc_admin` / `Admin123!`

These are for local development only.

## Recommended Manual Test Pass

### 1. Authentication

- Open `/accounts/login/`
- Confirm the login page renders correctly
- Log in as `requester_demo`
- Confirm header navigation changes to show authenticated controls
- Log out and confirm anonymous navigation is restored

### 2. SDLC Content

- Open `/`
- Confirm homepage styling and metrics render
- Open `Background`, `Controls`, `Risks`, `Templates`, and `SDLC Policy`
- Confirm the policy page renders readable content from the uploaded document
- Confirm template downloads work

### 3. Create A Change Request

Log in as `requester_demo`.

Create a new change request with:

- title
- change type
- business justification
- affected services
- implementation plan
- test/validation plan
- rollback plan
- outage/security/privacy/compliance impact
- linked items
- at least one implementation task

Expected result:

- request is created successfully
- a `CHG-...` identifier is assigned
- one final approval step is created automatically
- requester can view the request detail page

### 4. Submit The Request

From the request detail page:

- submit the request from `Draft` to `Submitted`

Expected result:

- workflow blocks submission if mandatory fields are missing
- activity log entry is created
- assigned approvers receive notification records

### 5. Verify Request Visibility

Use separate browsers or private windows.

- As `requester_demo`, confirm only own requests are visible
- As `approver_demo`, confirm only assigned approval work is visible
- As `auditor_demo`, confirm broad read access

Expected result:

- users do not see unrelated requests unless their role and assignment allow it

### 6. Risk Assessment Flow

On the request:

- add or update the risk assessment
- set a high residual risk if needed

Expected result:

- risk details are saved on the request
- no extra review or CAB step is created

### 7. Approval Flow

Test the final-approval path.

- As `approver_demo`, open the approval queue
- approve the request
- repeat the scenario with a second request and reject it

Expected result:

- approved request moves to `Approved`
- rejected request moves to `Rejected`
- requester can see the decision in the request history

### 8. Scheduling And Implementation

As `implementer_demo`:

- try to schedule a request without a completed risk assessment
- confirm it is blocked
- add planned start and end times
- schedule the request
- try to mark it `Implemented` without a planned window on a fresh request

Expected result:

- scheduling is blocked without completed risk assessment
- implementation is blocked without a planned window

### 9. Evidence And Closure

On an implemented or validated request:

- add evidence as a file or link
- add post-implementation results
- move the request toward `Closed`

Expected result:

- closure is blocked until both results and evidence exist
- unauthorized users cannot add evidence to someone else's request

### 10. Audit Trail

For one request, verify that the activity trail records:

- creation
- submission
- approval decisions
- risk updates
- state transitions
- evidence/comments

Expected result:

- each material workflow action is recorded with actor and timestamp

## Suggested Test Data

Use a few realistic scenarios:

- standard application release
- infrastructure restart
- emergency security patch
- high-risk database or payments change
- rollback scenario with failed validation

## Regression Checklist

Run this before sign-off on workflow changes:

- `python manage.py test change_management`
- `python manage.py check`
- manual login/logout test
- manual create -> approve -> schedule -> implement -> validate -> close flow
- unauthorized access check between two requester accounts
- approval and rejection flow
- template and policy page smoke check

## Current Gaps

The current project would benefit from more tests around:

- notification rendering in the UI
- overdue approval reminders
- file upload validation and size/type restrictions
- browser-level integration tests for full multi-user flows
- reporting and dashboard accuracy
- emergency-change specific handling

## Recommended Next Additions

If test coverage is expanded next, the best additions are:

1. request/response integration tests for full lifecycle transitions
2. assignment-aware visibility tests for each role
3. notification creation and unread-state tests
4. file upload validation and evidence-rule tests
5. browser automation for the primary happy path
