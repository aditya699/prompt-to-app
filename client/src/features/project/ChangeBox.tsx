import { useState } from "react";

import { Button, ErrorNote, Spinner } from "@/components/ui";
import { useRequestChange } from "@/hooks/queries";

/** Ask for a change to the app. Claude Code picks up the same session and edits the code. */
export function ChangeBox({
  projectId,
  busy,
  onQueued,
}: {
  projectId: number;
  busy: boolean;
  onQueued: () => void;
}) {
  const [prompt, setPrompt] = useState("");
  const change = useRequestChange(projectId);

  const submit = () => {
    if (prompt.trim().length < 3 || busy) return;
    change.mutate(prompt.trim(), {
      onSuccess: () => {
        setPrompt("");
        onQueued();
      },
    });
  };

  return (
    <form
      className="mt-3 flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) submit();
        }}
        rows={2}
        disabled={busy}
        placeholder={busy ? "Wait for this build to finish…" : "Ask for a change: “add a weekly chart”, “make it dark”…"}
        className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
        aria-label="Ask for a change"
      />
      {change.isError && <ErrorNote error={change.error} />}
      <div className="flex justify-end">
        <Button type="submit" disabled={busy || change.isPending || prompt.trim().length < 3}>
          {change.isPending && <Spinner />}
          Apply change
        </Button>
      </div>
    </form>
  );
}
