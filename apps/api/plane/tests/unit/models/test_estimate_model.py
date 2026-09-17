# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import Estimate, EstimatePoint, EstimateType, Project


@pytest.fixture
def project(db, workspace, create_user):
    return Project.objects.create(
        name="Test Project",
        identifier="TP",
        workspace=workspace,
        created_by=create_user,
    )


@pytest.mark.unit
class TestEstimateModel:
    """Test the Estimate model's TIME estimate type."""

    @pytest.mark.django_db
    def test_time_estimate_type_round_trips(self, project):
        estimate = Estimate.objects.create(
            name="Time Estimate",
            project=project,
            workspace=project.workspace,
            type=EstimateType.TIME,
        )

        assert estimate.type == "time"

        point = EstimatePoint.objects.create(
            estimate=estimate,
            project=project,
            workspace=project.workspace,
            key=1,
            value="1h",
        )

        assert point.estimate.type == EstimateType.TIME
        assert point.value == "1h"

    @pytest.mark.django_db
    def test_time_is_a_valid_estimate_type_choice(self):
        assert ("time", "Time") in EstimateType.choices
