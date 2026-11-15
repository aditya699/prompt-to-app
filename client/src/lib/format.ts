const RTF = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** "3 hours ago", "yesterday", ... */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return RTF.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

/** How long a build took: "1m 42s". */
export function duration(start: string | null, end: string | null): string {
  if (!start || !end) return "";
  const total = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  const minutes = Math.floor(total / 60);
  return minutes ? `${minutes}m ${total % 60}s` : `${total}s`;
}

export function money(usd: number | null): string {
  if (usd === null) return "";
  return usd === 0 ? "free" : `$${usd.toFixed(2)}`;
}
