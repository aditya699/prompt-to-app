import { useState } from "react";

import { Button } from "@/components/ui";

/** The deployed app in an iframe, with a phone/desktop toggle. */
export function Preview({ url, version }: { url: string | null; version: number }) {
  const [phone, setPhone] = useState(false);
  const [reloads, setReloads] = useState(0);

  if (!url) {
    return (
      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500 lg:h-[34rem]">
        Your app shows up here as soon as the first build is live.
      </div>
    );
  }
  // A new query string per build skips the browser cache after a redeploy.
  const src = `${url}?v=${version}-${reloads}`;
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2">
        <a href={url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-sm text-violet-700 hover:underline">
          {url}
        </a>
        <Button variant="ghost" onClick={() => setPhone((p) => !p)} className="hidden sm:inline-flex">
          {phone ? "Desktop" : "Phone"}
        </Button>
        <Button variant="ghost" onClick={() => setReloads((n) => n + 1)}>
          Reload
        </Button>
        <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(url)}>
          Copy link
        </Button>
      </div>
      <div className="flex justify-center bg-slate-100">
        <iframe
          key={src}
          src={src}
          title="App preview"
          // The app is untrusted code: let it run scripts and keep its own storage, nothing more.
          sandbox="allow-scripts allow-forms allow-same-origin allow-modals"
          className={`h-[30rem] border-0 bg-white lg:h-[32rem] ${phone ? "w-[375px]" : "w-full"}`}
        />
      </div>
    </div>
  );
}
