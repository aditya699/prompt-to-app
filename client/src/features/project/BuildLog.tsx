import { useEffect, useRef } from "react";

import type { Build, LogEvent } from "@/api/types";
import { ACTIVE_STATUSES } from "@/api/types";
import { Button, Spinner, StatusBadge } from "@/components/ui";
import type { BuildLogState } from "@/hooks/useBuildLog";

/** A terminal-style view of what the agent is doing, line by line. */
export function BuildLog({
  build,
  log,
  onCancel,
  cancelling,
}: {
  build: Build;
  log: BuildLogState;
  onCancel: () => void;
  cancelling: boolean;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [log.events.length]);

  const active = ACTIVE_STATUSES.includes(build.status) && !log.done;
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950 text-slate-200">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-4 py-2">
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="font-medium text-white">Build #{build.number}</span>
          <StatusBadge status={doneStatus(log.done) ?? build.status} />
        </div>
        {active && (
          <Button variant="ghost" onClick={onCancel} disabled={cancelling} className="text-slate-300 hover:bg-slate-800">
            Cancel
          </Button>
        )}
      </div>
      <p className="border-b border-slate-800 px-4 py-2 text-sm text-slate-400">“{build.prompt}”</p>
      <div className="log-scroll h-80 overflow-y-auto px-4 py-3 font-mono text-[13px] leading-6 lg:h-[26rem]">
        {log.events.map((event) => (
          <LogLine key={event.seq} event={event} />
        ))}
        {active && (
          <div className="flex items-center gap-2 text-slate-500">
            <Spinner className="h-3 w-3" /> {build.status === "queued" ? "Waiting for a free builder…" : "Working…"}
          </div>
        )}
        {log.error && !log.connected && !log.done && (
          <p className="text-amber-400">Lost the connection to the log; retrying…</p>
        )}
        <div ref={bottom} />
      </div>
    </div>
  );
}

function doneStatus(done: LogEvent | null) {
  const status = done?.data?.status;
  return typeof status === "string" ? (status as Build["status"]) : null;
}

function LogLine({ event }: { event: LogEvent }) {
  switch (event.type) {
    case "status":
      return <p className="text-slate-500">· {event.text}</p>;
    case "tool":
      return (
        <p className="truncate text-sky-300" title={event.text}>
          <span className="text-slate-600">› </span>
          {event.text}
        </p>
      );
    case "message":
      return <p className="my-1 whitespace-pre-wrap break-words font-sans text-sm text-slate-100">{event.text}</p>;
    case "error":
      return <p className="whitespace-pre-wrap text-red-400">✕ {event.text}</p>;
    case "done": {
      const url = typeof event.data?.url === "string" ? event.data.url : null;
      if (event.data?.status === "live" && url) {
        return (
          <p className="mt-2 font-sans text-sm text-emerald-300">
            ✓ Live at{" "}
            <a href={url} target="_blank" rel="noreferrer" className="break-all underline">
              {url}
            </a>
          </p>
        );
      }
      return <p className="mt-2 whitespace-pre-wrap font-sans text-sm text-slate-400">{event.text}</p>;
    }
  }
}
