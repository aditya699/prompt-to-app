import { useEffect, useState } from "react";

import { api } from "@/api/endpoints";
import type { LogEvent } from "@/api/types";

export interface BuildLogState {
  events: LogEvent[];
  done: LogEvent | null;
  connected: boolean;
  error: string | null;
}

/**
 * Follows one build's log over SSE. The server replays what is saved and then
 * streams new lines until a `done` event. If the connection drops mid-build,
 * we reconnect from the last line we have.
 */
export function useBuildLog(buildId: number | null): BuildLogState {
  const [state, setState] = useState<BuildLogState>({
    events: [],
    done: null,
    connected: false,
    error: null,
  });

  useEffect(() => {
    if (buildId === null) return;
    const controller = new AbortController();
    let events: LogEvent[] = [];
    let done: LogEvent | null = null;
    setState({ events, done, connected: false, error: null });

    const run = async () => {
      for (let attempt = 0; attempt < 5 && !done && !controller.signal.aborted; attempt++) {
        try {
          const after = events[events.length - 1]?.seq ?? 0;
          setState((s) => ({ ...s, connected: true, error: null }));
          await api.followBuild(
            buildId,
            after,
            (event) => {
              if (event.type === "done") done = event;
              events = [...events, event];
              setState({ events, done, connected: !done, error: null });
            },
            controller.signal,
          );
          if (done) return;
        } catch (err) {
          if (controller.signal.aborted) return;
          setState((s) => ({ ...s, connected: false, error: String(err) }));
        }
        await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)));
      }
      setState((s) => ({ ...s, connected: false }));
    };
    void run();
    return () => controller.abort();
  }, [buildId]);

  return state;
}
