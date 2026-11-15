import { useHealth } from "@/hooks/queries";
import { navigate } from "@/lib/router";

export function Header() {
  const { data: health, isError } = useHealth();
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <button onClick={() => navigate({ page: "home" })} className="flex items-center gap-2">
          <img src="/logo.svg" alt="" className="h-7 w-7" />
          <span className="font-semibold">Prompt to App</span>
        </button>
        <div className="text-right text-xs text-slate-500">
          {isError && <span className="text-red-600">Can't reach the API</span>}
          {health && (
            <span title="Set BUILDER in server/.env">
              {health.builder === "fake" ? (
                <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">Demo builder (no key)</span>
              ) : (
                <>Claude Code · {health.model}</>
              )}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
