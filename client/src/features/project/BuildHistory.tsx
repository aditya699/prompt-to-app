import type { Build } from "@/api/types";
import { StatusBadge } from "@/components/ui";
import { duration, money, timeAgo } from "@/lib/format";

/** Every build of the project, newest first. Click one to read its log. */
export function BuildHistory({
  builds,
  selectedId,
  onSelect,
}: {
  builds: Build[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">History</h2>
      <ol className="flex flex-col gap-2">
        {[...builds].reverse().map((build) => (
          <li key={build.id}>
            <button
              onClick={() => onSelect(build.id)}
              className={`flex w-full flex-col gap-1 rounded-lg border bg-white px-3 py-2 text-left text-sm transition hover:border-violet-300 ${
                build.id === selectedId ? "border-violet-400" : "border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">#{build.number}</span>
                <StatusBadge status={build.status} />
              </div>
              <p className="line-clamp-2 text-slate-600">{build.prompt}</p>
              <p className="text-xs text-slate-400">
                {[
                  timeAgo(build.created_at),
                  duration(build.started_at, build.finished_at),
                  build.turns ? `${build.turns} turns` : "",
                  money(build.cost_usd),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {build.error && <p className="text-xs text-red-600">{build.error}</p>}
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
