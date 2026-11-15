import type { Project } from "@/api/types";
import { EmptyState, ErrorNote, Spinner, StatusBadge } from "@/components/ui";
import { useProjects } from "@/hooks/queries";
import { timeAgo } from "@/lib/format";
import { navigate } from "@/lib/router";

export function ProjectGrid() {
  const { data, isLoading, error } = useProjects();
  return (
    <section className="mx-auto mt-14 max-w-6xl">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Your apps</h2>
      {isLoading && <Spinner className="text-slate-400" />}
      {error && <ErrorNote error={error} />}
      {data?.length === 0 && (
        <EmptyState title="No apps yet">Pick an example above, or describe your own.</EmptyState>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((project) => <ProjectCard key={project.id} project={project} />)}
      </div>
    </section>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const status = project.latest_build?.status ?? project.status;
  return (
    <button
      onClick={() => navigate({ page: "project", id: project.id })}
      className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-violet-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-semibold">{project.name}</span>
        <StatusBadge status={status} />
      </div>
      <p className="line-clamp-2 text-sm text-slate-600">{project.prompt}</p>
      <span className="mt-auto text-xs text-slate-400">Updated {timeAgo(project.updated_at)}</span>
    </button>
  );
}
