/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// components
import { PageHead } from "@/components/core/page-title";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
// local imports
import { WorkspaceActiveCyclesList } from "@/components/active-cycles/workspace-active-cycles-list";

function WorkspaceActiveCyclesPage() {
  const { workspaceSlug } = useParams();
  const { currentWorkspace } = useWorkspace();
  // derived values
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace?.name} - Active Cycles` : undefined;

  return (
    <>
      <PageHead title={pageTitle} />
      <WorkspaceActiveCyclesList workspaceSlug={workspaceSlug?.toString() ?? ""} />
    </>
  );
}

export default observer(WorkspaceActiveCyclesPage);
