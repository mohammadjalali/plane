# Fork Changelog

Tracks every change made in this self-hosted CE fork beyond upstream Plane,
per the ground rules and scoping in `FORK_PLAN.md`.

## Item A — sidebar "PRO" badge shown on non-gated items

Category: A (bug fix, no new functionality).

- `apps/web/core/components/workspace/sidebar/workspace-menu-item.tsx` —
  only render `<UpgradeBadge/>` when `item.key === "active-cycles"` (the key
  used by this item's own data source, `SIDEBAR_WORKSPACE_MENU_ITEMS` in
  `workspace-menu.tsx`), matching the conditional pattern already used in the
  sibling `extended-sidebar-item.tsx` (which keys off `"active_cycles"` from
  its own, differently-keyed data source). Previously the badge rendered next
  to every workspace sidebar item (Projects, Views, Active Cycles, Analytics).

## Item B — Time-based Estimates

Category: B (build from scratch, backed entirely by already-open-sourced
models/endpoints in this repo).

- `apps/api/plane/db/models/estimate.py` — added `TIME = "time", "Time"` to
  `EstimateType.TextChoices`.
- `apps/api/plane/db/models/__init__.py` — export `EstimateType`.
- `apps/api/plane/db/migrations/0123_alter_estimate_type.py` — additive
  migration for the new `EstimateType` choice (generated via
  `manage.py makemigrations`, verified clean with `--check`).
- `packages/constants/src/estimates.ts` — `ESTIMATE_SYSTEMS.time.is_ee` set
  to `false`.
- `apps/web/core/components/estimates/create/helper.tsx` —
  `isEstimateSystemEnabled()` returns `true` for `EEstimateSystem.TIME`.
- Tests: `apps/api/plane/tests/unit/models/test_estimate_model.py`
  (Estimate/EstimatePoint round-trip with `type=TIME`).

No serializer/view changes were needed — `EstimateSerializer` uses
`fields = "__all__"`, so DRF derives the field's valid choices directly from
the model's `EstimateType.choices`.

## Item C — Workspace-wide Active Cycles page

Category: B (new read-only aggregation endpoint over the existing, fully-open
`Cycle` model; no EE code involved).

- `apps/api/plane/app/views/workspace/cycle.py` — new
  `WorkspaceActiveCyclesEndpoint`, filtering `Cycle` by
  `start_date__lte=now, end_date__gte=now` across all projects in the
  workspace the requesting user is an active member of (mirrors the existing
  `WorkspaceCyclesEndpoint` scoping/annotations), paginated via
  `BasePaginator.paginate`.
- `apps/api/plane/app/views/__init__.py`,
  `apps/api/plane/app/urls/workspace.py` — export/register
  `GET /api/workspaces/{slug}/active-cycles/`.
- `apps/web/core/store/cycle.store.ts` — new `fetchWorkspaceActiveCycles`
  action populating `cycleMap` from the new endpoint (mirrors
  `fetchWorkspaceCycles`).
- `apps/web/core/components/active-cycles/workspace-active-cycles-list.tsx`
  (new) — fetches active cycles workspace-wide, groups by project, and
  renders each project's active cycle using the existing
  `ActiveCycleRoot`/`CyclesListItem` widgets (same rich progress/productivity/
  stats cards used on the per-project cycles page).
- `apps/web/app/(all)/[workspaceSlug]/(projects)/active-cycles/page.tsx` —
  renders `WorkspaceActiveCyclesList` instead of the static
  `WorkspaceActiveCyclesUpgrade` marketing CTA.
- Removed `apps/web/core/components/active-cycles/workspace-active-cycles-upgrade.tsx`
  (dead code once the real page shipped; its CTA image assets were only
  referenced from this file).
- Tests: `apps/api/plane/tests/contract/app/test_workspace_active_cycles_app.py`
  (workspace membership scoping — mirrors the existing
  `test_workspace_cycles_modules_project_scope_app.py` pattern — plus
  active/upcoming/completed date-window filtering).

**Merge-conflict warning** (per `FORK_PLAN.md`): upstream Plane will keep
shipping `active-cycles/page.tsx` as the static upgrade card on every
release. This file will permanently diverge from upstream.

## Verification

- `docker compose -f docker-compose-test.yml run --rm api-tests pytest` —
  full suite: 582 passed. (3 pre-existing, unrelated `test_projects_lite.py`
  failures are a rate-limit test-ordering flake — pass in isolation,
  unaffected by these changes.)
- `manage.py makemigrations --check --dry-run` — clean after adding
  `0123_alter_estimate_type.py`.
- `pnpm turbo run check:types --filter=web` — clean.
- `pnpm turbo run check:lint --filter=web` — 0 errors (779 pre-existing
  warnings, unchanged, well under the ratchet).
