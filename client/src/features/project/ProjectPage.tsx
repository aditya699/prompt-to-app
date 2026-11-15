import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ACTIVE_STATUSES } from "@/api/types";
import { Button, ErrorNote, Spinner, StatusBadge } from "@/components/ui";
import { keys, useCancelBuild, useDeleteProject, useProject } from "@/hooks/queries";
import { useBuildLog } from "@/hooks/useBuildLog";
import { navigate } from "@/lib/router";

import { BuildHistory } from "./BuildHistory";
import { BuildLog } from "./BuildLog";
import { ChangeBox } from "./ChangeBox";
import { Preview } from "./Preview";

export function ProjectPage({ id }: { id: number }) {
  const client = useQueryClient();
  const { data: project, isLoading, error } = useProject(id);
  const cancel = useCancelBuild(id);
  const remove = useDeleteProject();
  // null = follow the latest build; a number = the user picked one from the history.
  const [pickedId, setPickedId] = useState<number | null>(null);

  const latest = project?.builds[project.builds.length - 1] ?? null;
  const selected = project?.builds.find((b) => b.id === pickedId) ?? latest;
  const log = useBuildLog(selected?.id ?? null);

  // When the log says the build ended, refresh the project (status, URL, cost).
  useEffect(() => {
    if (log.done) {
      void client.invalidateQueries({ queryKey: keys.project(id) });
      void client.invalidateQueries({ queryKey: keys.projects });
    }
  }, [log.done, client, id]);

  if (isLoading) return <Spinner className="mx-auto mt-20 block text-slate-400" />;
  if (error || !project) return <ErrorNote error={error ?? "Project not found"} />;

  const busy = latest !== null && ACTIVE_STATUSES.includes(latest.status) && !(latest.id === selected?.id && log.done);
  const lastLive = [...project.builds].reverse().find((b) => b.status === "live");

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button onClick={() => navigate({ page: "home" })} className="text-sm text-slate-500 hover:text-slate-800">
          ← All apps
        </button>
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <StatusBadge status={project.status} />
        <div className="ml-auto flex gap-2">
          {project.url && (
            <a
              href={project.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-violet-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-800"
            >
              Open app ↗
            </a>
          )}
          <Button
            variant="danger"
            disabled={remove.isPending}
            onClick={() => {
              if (window.confirm(`Delete ${project.name}? Its link stops working.`)) {
                remove.mutate(project.id, { onSuccess: () => navigate({ page: "home" }) });
              }
            }}
          >
            Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div className="min-w-0">
          {selected && (
            <BuildLog
              build={selected}
              log={log}
              cancelling={cancel.isPending}
              onCancel={() => cancel.mutate(selected.id)}
            />
          )}
          <ChangeBox
            projectId={project.id}
            busy={busy}
            onQueued={() => {
              setPickedId(null);
              void client.invalidateQueries({ queryKey: keys.project(id) });
            }}
          />
          <BuildHistory builds={project.builds} selectedId={selected?.id ?? null} onSelect={setPickedId} />
        </div>
        <div className="lg:sticky lg:top-6 lg:self-start">
          <Preview url={project.url} version={lastLive?.id ?? 0} />
        </div>
      </div>
    </div>
  );
}
