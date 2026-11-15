// Mirrors the server's Pydantic models in server/app/schemas/project.py.

export type BuildStatus = "queued" | "building" | "deploying" | "live" | "failed" | "cancelled";
export type ProjectStatus = "draft" | "building" | "live" | "failed";

export interface Build {
  id: number;
  project_id: number;
  number: number;
  prompt: string;
  status: BuildStatus;
  builder: string;
  cost_usd: number | null;
  turns: number | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Project {
  id: number;
  slug: string;
  name: string;
  prompt: string;
  status: ProjectStatus;
  url: string | null;
  created_at: string;
  updated_at: string;
  latest_build: Build | null;
}

export interface ProjectDetail extends Project {
  builds: Build[];
}

export type LogEventType = "status" | "message" | "tool" | "error" | "done";

export interface LogEvent {
  seq: number;
  type: LogEventType;
  text: string;
  data?: Record<string, unknown> | null;
  created_at: string;
}

export interface Health {
  status: string;
  builder: "claude_code" | "fake";
  model: string | null;
  deployer: string;
  sandbox: boolean;
  max_concurrent_builds: number;
}

export interface Example {
  label: string;
  prompt: string;
}

export const ACTIVE_STATUSES: BuildStatus[] = ["queued", "building", "deploying"];
