# Community Edition Fork — Feature Plan

Working plan for this self-hosted CE fork: what's actually restricted in this
codebase vs. what's marketing/EE-only, and what to build. Written 2026-09-17
after an audit of `apps/api` + `apps/web`/`packages` for license checks,
quotas, feature flags, and disabled UI.

## Ground rules (do not violate)

1. Never bypass/spoof/patch a license, subscription, activation, or
   entitlement check. **None currently exist in this repo** — see finding 0
   below — but if a future upstream merge adds one, treat it as off-limits
   by default.
2. Never make the app believe it holds a paid license it doesn't.
3. Never copy code from `plane-ee` or Plane Cloud's closed-source backend.
   Only reimplement equivalent behavior from scratch, using models/endpoints
   already open-sourced in this repo.
4. If unsure whether something is CE or a real commercial gate, stop and
   flag it — don't touch it.

## Finding 0 — there is nothing to unlock here

Audited `apps/api/plane/license/`, all `apps/api/plane/app/views`, and every
`EProductSubscriptionEnum`/`UpgradeBadge`/billing reference in
`apps/web`/`packages`. Result: **no license server client, no entitlement
API, no subscription model, no feature-flag SDK anywhere in this codebase.**
`InstanceEdition` is hardcoded to `PLANE_COMMUNITY` and used only for
telemetry. Confirmed no hardcoded member/project/workspace quotas anywhere
in the Django views.

What Plane's real Pro/Business self-hosted tiers add (per
`plane.so/pricing`, checked 2026-09-17):

| Plan             | Price                    | Adds                                                                                                                                       |
| ---------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Free (Community) | $0, up to 12 users       | Projects, work items, cycles, modules, 5 layouts, intake, estimates, project pages                                                         |
| Pro              | $8/user/mo ($6 annual)   | Custom work item types, workspace wiki, time tracking, templates, dashboards, initiatives, teamspaces, integrations, SAML/OIDC self-hosted |
| Business         | $15/user/mo ($13 annual) | Project templates, recurring work items, intake email/forms, nested pages, workflows, customer profiles, advanced dashboard widgets        |
| Enterprise Grid  | Custom                   | LDAP, audit logs, multi-workflow approvals, managed deployments                                                                            |

None of that column's functionality (Time Tracking, Custom Work Item Types,
Workflows, Teamspaces, nested Pages, LDAP, audit log, etc.) has any code
presence in this repo — it isn't a flag to flip, it was never shipped here.
Getting real parity means building each one from scratch as original OSS
code. The two items below are the only ones that turned out to be
genuinely partially-built already.

## Item A — sidebar "PRO" badge shown on non-gated items (quick fix)

- **File**: `apps/web/core/components/workspace/sidebar/workspace-menu-item.tsx`
  → `SidebarWorkspaceMenuItem`
- **Bug**: renders `<UpgradeBadge/>` next to _every_ workspace sidebar item
  (Projects, Views, Active Cycles, Analytics), not just Active Cycles (the
  only one of the four that's actually unavailable). Compare the correct
  pattern in the sibling file `extended-sidebar-item.tsx`, which already
  conditions the badge on `item.key === "active_cycles"`.
- **Fix**: same conditional in `workspace-menu-item.tsx` — only show the
  badge when `item.key === "active-cycles"`.
- **Backend change**: none needed — Projects/Views/Analytics are already
  fully functional in CE.
- **Test**: story/unit test asserting the badge renders only for the
  active-cycles item.
- **Effort**: trivial, ~10 min.

## Item B — Time-based Estimates (Category B — build from scratch)

Frontend already has a complete "Time" estimate template
(`packages/constants/src/estimates.ts` → `ESTIMATE_SYSTEMS.time`) but it's
marked `is_ee: true` and hardcoded off in
`apps/web/core/components/estimates/create/helper.tsx` →
`isEstimateSystemEnabled()`. The real blocker is the backend: `EstimateType`
in `apps/api/plane/db/models/estimate.py` only has `CATEGORIES` and
`POINTS` — no `TIME` choice exists in the DB at all.

- **Architecture**: add `TIME` as a third value of the existing
  `EstimateType` enum. No new tables — `EstimatePoint.value` is already a
  free-text `CharField`, so time values (`"1h"`, `"4h"`, …) fit the existing
  schema.
- **Database**: one migration in `apps/api/plane/db/migrations/` adding
  `TIME = "time", "Time"` to `EstimateType.TextChoices`. Additive only, no
  data migration, no change to existing rows.
- **API**: update wherever `EstimateType` is validated (project estimate
  serializer/view under `apps/api/plane/app/views/project/estimate.py` and
  related serializers) to accept `TIME`. Update
  `apps/api/plane/settings/openapi.py` if it enumerates estimate types.
- **Backend implementation**: enum change + validation change only, no new
  endpoints.
- **Frontend implementation**:
  - `packages/constants/src/estimates.ts`: set `ESTIMATE_SYSTEMS.time.is_ee
= false`.
  - `apps/web/core/components/estimates/create/helper.tsx`:
    `isEstimateSystemEnabled()` returns `true` for `EEstimateSystem.TIME`.
  - No other UI change needed — `EstimateCreateStageOne` already renders
    the "Time"/"hours" template correctly once `is_available && !is_ee`.
    i18n keys (`project_settings.estimates.systems.time.*`) already exist.
- **Permissions**: unchanged (existing "project admin can configure
  estimates" rule).
- **Tests**:
  - Backend: pytest creating an `Estimate(type=TIME)` with hour-labeled
    points, asserting it round-trips like `points`/`categories`.
  - Frontend: unit/story test asserting the Time option is selectable
    (not disabled) and produces the hours template.
- **Effort**: small-moderate, ~0.5–1 day incl. tests.

## Item C — Workspace-wide Active Cycles page (Category B — build from scratch)

`apps/web/app/(all)/[workspaceSlug]/(projects)/active-cycles/page.tsx`
unconditionally renders `WorkspaceActiveCyclesUpgrade` (a static marketing
CTA) — there is no code path in CE that ever shows real data here. The
frontend service `cycleService.workspaceActiveCycles()`
(`packages/services/src/cycle/cycle.service.ts`) already calls
`GET /api/workspaces/{slug}/active-cycles/`, but that route doesn't exist
anywhere in `apps/api/plane/app/urls/cycle.py` — confirmed by reading the
full urls file, which only has per-project cycle endpoints. This is a
genuine gap to fill, not a flag to flip.

- **Architecture**: new read-only aggregation endpoint over the existing,
  fully-open `Cycle` model — reuses the same serializer/permission scoping
  already used per-project. No EE code involved or needed.
- **Database**: no new models. Optional: composite index on
  `(workspace_id, project_id, start_date, end_date)` on `Cycle` if the
  aggregate query is slow at scale — check with `EXPLAIN` first, don't
  add speculatively.
- **API**: add `GET /api/workspaces/{slug}/active-cycles/` to
  `apps/api/plane/app/urls/cycle.py`, backed by a new
  `WorkspaceActiveCyclesEndpoint` (new file or added to
  `apps/api/plane/app/views/cycle.py`), scoped through the existing
  workspace/project membership permission classes so a user only sees
  cycles from projects they belong to.
- **Backend implementation**: filter
  `Cycle.objects.filter(workspace__slug=slug, start_date__lte=now,
end_date__gte=now)` (matches Plane's own existing per-project "active"
  definition), paginate, serialize with the existing `CycleSerializer`,
  reuse `CycleProgressEndpoint`'s existing progress-annotation logic rather
  than duplicating it.
- **Frontend implementation**: in
  `active-cycles/page.tsx`, replace the unconditional
  `<WorkspaceActiveCyclesUpgrade/>` with a real fetch via
  `cycleService.workspaceActiveCycles()` (already exists, currently dead
  code hitting a 404) and a list/grid of cycle cards. Keep the existing
  empty-state illustration assets for the zero-active-cycles case.
- **Permissions**: workspace member/admin (matches the existing sidebar
  `access` array for the `active-cycles` nav item already). No new roles.
- **Migrations**: none, unless the optional index above is added.
- **Tests**:
  - Backend: pytest with 2+ projects asserting correct membership scoping
    and correct "active" date filtering.
  - Frontend: test/story asserting the page renders real cycle cards
    instead of the upgrade CTA.
- **Merge-conflict warning**: upstream Plane will keep shipping
  `active-cycles/page.tsx` as the static upgrade card on every release.
  This file will permanently diverge from upstream — expect a manual merge
  resolution on this file on every future `git merge`/rebase from
  upstream, not just once.
- **Effort**: moderate, ~1–2 days incl. tests.

## Flagged for later, not scoped yet

Real Pro/Business/Enterprise features with **zero code presence** in this
repo (per Finding 0's pricing table). Each needs its own from-scratch
design pass before starting — do not attempt any of these as a quick flag
flip:

- Time Tracking + Worklogs (distinct from Item B's estimate labels — real
  tracking needs start/stop timers and a worklog model)
- Custom Work Item Types
- Workflows / status-transition rules with approvals
- Teamspaces
- Workspace Wiki / nested Pages
- Project Templates, recurring work items
- Intake via email/forms
- Customer profiles, advanced dashboard widgets
- LDAP, audit logs, SAML/OIDC self-hosted

## Execution order when picked up

1. Item A (sidebar badge) — do first, trivial, no risk.
2. Item B (Time Estimates) — self-contained, low merge-conflict risk.
3. Item C (Workspace Active Cycles) — larger, has an ongoing upstream
   merge-conflict cost; do when there's time to own that maintenance.
4. Before calling any of A/B/C done:
   - Run the existing test suites (`pnpm check`, `pnpm --filter=live test`,
     the dockerized pytest suite per `AGENTS.md`/`CLAUDE.md`).
   - Add the new tests listed under each item.
   - Run `makemigrations --check` for Item B's migration.
   - Boot `docker-compose-local.yml` and `docker-compose-test.yml` to
     confirm the new migration applies cleanly.
   - Update `CHANGELOG_FORK.md` with every file touched, why, and its
     category (A/B).
5. Pick one item from "Flagged for later" only when there's a specific one
   worth the investment — scope it the same way as B/C above before
   writing any code.
