# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the workspace-wide active cycles endpoint.

``WorkspaceActiveCyclesEndpoint`` aggregates "currently active" cycles
(``start_date <= now <= end_date``) across every project in a workspace the
requesting user is an active member of, powering the workspace Active
Cycles page. Coverage:

- membership scoping (mirrors ``WorkspaceCyclesEndpoint``/``WorkspaceModulesEndpoint``)
- "active" date-window filtering excludes upcoming/completed/draft cycles
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Cycle, Project, ProjectMember, User, WorkspaceMember

ACTIVE_CYCLES_URL = "/api/workspaces/{slug}/active-cycles/"


@pytest.fixture
def project(db, workspace, create_user):
    """A project in the fixture workspace; ``create_user`` is an active member."""
    project = Project.objects.create(
        name="Private Project",
        identifier="PP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        project=project, member=create_user, workspace=workspace, role=20
    )
    return project


@pytest.fixture
def other_project(db, workspace, create_user):
    """A second project in the same workspace that ``create_user`` is NOT a member of."""
    unique_id = uuid4().hex[:8]
    owner = User.objects.create(
        email=f"owner-{unique_id}@plane.so",
        username=f"owner_{unique_id}",
        first_name="Owner",
        last_name="User",
    )
    project = Project.objects.create(
        name="Other Project",
        identifier="OP",
        workspace=workspace,
        created_by=owner,
    )
    ProjectMember.objects.create(project=project, member=owner, workspace=workspace, role=20)
    project.owner_user = owner
    return project


@pytest.fixture
def active_cycle(db, workspace, project, create_user):
    """A cycle whose date range spans the current time."""
    return Cycle.objects.create(
        name="Active Cycle",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=1),
    )


@pytest.fixture
def upcoming_cycle(db, workspace, project, create_user):
    """A cycle that hasn't started yet — must not be reported as active."""
    return Cycle.objects.create(
        name="Upcoming Cycle",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        start_date=timezone.now() + timedelta(days=5),
        end_date=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def completed_cycle(db, workspace, project, create_user):
    """A cycle that already ended — must not be reported as active."""
    return Cycle.objects.create(
        name="Completed Cycle",
        project=project,
        workspace=workspace,
        owned_by=create_user,
        start_date=timezone.now() - timedelta(days=10),
        end_date=timezone.now() - timedelta(days=5),
    )


@pytest.fixture
def outsider_client(db, workspace):
    """Session client for a workspace member who is NOT in ``project``."""
    unique_id = uuid4().hex[:8]
    outsider = User.objects.create(
        email=f"outsider-{unique_id}@plane.so",
        username=f"outsider_{unique_id}",
        first_name="Outsider",
        last_name="User",
    )
    outsider.set_password("test-password")
    outsider.save()
    WorkspaceMember.objects.create(workspace=workspace, member=outsider, role=15)
    client = APIClient()
    client.force_authenticate(user=outsider)
    return client


@pytest.mark.contract
class TestWorkspaceActiveCyclesEndpoint:
    @pytest.mark.django_db
    def test_active_cycle_visible_to_project_member(self, session_client, workspace, active_cycle):
        response = session_client.get(ACTIVE_CYCLES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        ids = {str(row["id"]) for row in response.data["results"]}
        assert str(active_cycle.id) in ids

    @pytest.mark.django_db
    def test_active_cycle_hidden_from_non_project_member(self, outsider_client, workspace, active_cycle):
        response = outsider_client.get(ACTIVE_CYCLES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    @pytest.mark.django_db
    def test_excludes_other_project_cycles(self, session_client, workspace, project, other_project, create_user):
        other_active_cycle = Cycle.objects.create(
            name="Other Active Cycle",
            project=other_project,
            workspace=workspace,
            owned_by=other_project.owner_user,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
        )
        response = session_client.get(ACTIVE_CYCLES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        ids = {str(row["id"]) for row in response.data["results"]}
        assert str(other_active_cycle.id) not in ids

    @pytest.mark.django_db
    def test_excludes_upcoming_and_completed_cycles(
        self, session_client, workspace, active_cycle, upcoming_cycle, completed_cycle
    ):
        response = session_client.get(ACTIVE_CYCLES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        ids = {str(row["id"]) for row in response.data["results"]}
        assert ids == {str(active_cycle.id)}
