/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import { useTranslation } from "@plane/i18n";
// components
import { ActiveCycleRoot } from "@/components/cycles/active-cycle/root";
import { CycleListGroupHeader } from "@/components/cycles/list/cycle-list-group-header";
import { CycleModuleListLayoutLoader } from "@/components/ui/loader/cycle-module-list-loader";
// hooks
import { useCycle } from "@/hooks/store/use-cycle";
import { useProject } from "@/hooks/store/use-project";

type Props = {
  workspaceSlug: string;
};

export const WorkspaceActiveCyclesList = observer(function WorkspaceActiveCyclesList(props: Props) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  // store hooks
  const { fetchWorkspaceActiveCycles } = useCycle();
  const { getProjectById } = useProject();

  const { data: activeCycles, isLoading } = useSWR(
    workspaceSlug ? `WORKSPACE_ACTIVE_CYCLES_${workspaceSlug}` : null,
    workspaceSlug ? () => fetchWorkspaceActiveCycles(workspaceSlug, "100:0:0", 100) : null
  );

  const projectIds = useMemo(() => {
    const uniqueProjectIds = new Set<string>();
    (activeCycles?.results ?? []).forEach((cycle) => {
      if (cycle.project_id) uniqueProjectIds.add(cycle.project_id);
    });
    return Array.from(uniqueProjectIds);
  }, [activeCycles]);

  const cyclesByProjectId = useMemo(() => {
    const grouped: Record<string, string> = {};
    (activeCycles?.results ?? []).forEach((cycle) => {
      if (cycle.project_id && cycle.id) grouped[cycle.project_id] = cycle.id;
    });
    return grouped;
  }, [activeCycles]);

  if (isLoading && !activeCycles) return <CycleModuleListLayoutLoader />;

  if (projectIds.length === 0) {
    return (
      <EmptyStateDetailed
        assetKey="cycle"
        title={t("project_cycles.empty_state.active.title")}
        description={t("project_cycles.empty_state.active.description")}
        rootClassName="py-10 h-auto"
      />
    );
  }

  return (
    <div className="flex flex-col">
      {projectIds.map((projectId) => {
        const project = getProjectById(projectId);
        const cycleId = cyclesByProjectId[projectId];
        if (!cycleId) return null;
        return (
          <div key={projectId} className="flex flex-col border-b border-subtle">
            <CycleListGroupHeader type="current" title={project?.name ?? ""} isExpanded />
            <ActiveCycleRoot workspaceSlug={workspaceSlug} projectId={projectId} cycleId={cycleId} showHeader={false} />
          </div>
        );
      })}
    </div>
  );
});
