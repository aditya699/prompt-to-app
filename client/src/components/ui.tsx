// Small presentational building blocks shared across features.
import type { ReactNode } from "react";

import type { BuildStatus, ProjectStatus } from "@/api/types";

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      aria-hidden
    />
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  className = "",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  className?: string;
  type?: "button" | "submit";
}) {
  const styles = {
    primary: "bg-violet-700 text-white hover:bg-violet-800",
    secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100",
    danger: "text-red-600 hover:bg-red-50",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

const STATUS_STYLES: Record<BuildStatus | ProjectStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-slate-100 text-slate-600" },
  queued: { label: "Queued", className: "bg-slate-100 text-slate-600" },
  building: { label: "Building", className: "bg-amber-100 text-amber-800" },
  deploying: { label: "Deploying", className: "bg-sky-100 text-sky-800" },
  live: { label: "Live", className: "bg-emerald-100 text-emerald-800" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700" },
  cancelled: { label: "Cancelled", className: "bg-slate-100 text-slate-500" },
};

export function StatusBadge({ status }: { status: BuildStatus | ProjectStatus }) {
  const style = STATUS_STYLES[status];
  const active = status === "building" || status === "deploying" || status === "queued";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${style.className}`}>
      {active && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {style.label}
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
      <p className="font-medium text-slate-700">{title}</p>
      {children && <div className="mt-2 text-sm">{children}</div>}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>;
}
