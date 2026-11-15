import { useState } from "react";

import { Button, ErrorNote, Spinner } from "@/components/ui";
import { useCreateProject, useExamples } from "@/hooks/queries";
import { navigate } from "@/lib/router";

/** The big "describe your app" box, plus example prompts to start from. */
export function PromptBox() {
  const [prompt, setPrompt] = useState("");
  const examples = useExamples();
  const create = useCreateProject();

  const submit = () => {
    if (prompt.trim().length < 8) return;
    create.mutate(prompt.trim(), {
      onSuccess: (project) => navigate({ page: "project", id: project.id }),
    });
  };

  return (
    <section className="mx-auto max-w-3xl text-center">
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">What should we build?</h1>
      <p className="mt-2 text-slate-600">
        Describe an app. Claude Code builds it on your server and gives you a link.
      </p>
      <form
        className="mt-6 rounded-2xl border border-slate-200 bg-white p-3 text-left shadow-sm focus-within:border-violet-400"
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
          rows={4}
          placeholder="Create a web app that will help me track my workouts…"
          className="w-full resize-none bg-transparent p-2 text-base outline-none placeholder:text-slate-400"
          aria-label="Describe your app"
        />
        <div className="flex items-center justify-between gap-3 px-2 pb-1">
          <span className="hidden text-xs text-slate-400 sm:inline">Ctrl + Enter to build</span>
          <Button type="submit" disabled={create.isPending || prompt.trim().length < 8} className="ml-auto px-4 py-2">
            {create.isPending ? <Spinner /> : null}
            Build it
          </Button>
        </div>
      </form>
      {create.isError && (
        <div className="mt-3 text-left">
          <ErrorNote error={create.error} />
        </div>
      )}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {examples.data?.map((example) => (
          <button
            key={example.label}
            onClick={() => setPrompt(example.prompt)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-600 hover:border-violet-300 hover:text-violet-700"
          >
            {example.label}
          </button>
        ))}
      </div>
    </section>
  );
}
