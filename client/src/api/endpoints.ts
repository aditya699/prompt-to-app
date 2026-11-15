// One function per API endpoint. Components use these through the hooks in src/hooks.
import { readSSE, request } from "./http";
import type { Build, Example, Health, LogEvent, Project, ProjectDetail } from "./types";

export const api = {
  health: () => request<Health>("/api/health"),
  examples: () => request<Example[]>("/api/examples"),

  listProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: number) => request<ProjectDetail>(`/api/projects/${id}`),
  createProject: (prompt: string) =>
    request<ProjectDetail>("/api/projects", { method: "POST", body: JSON.stringify({ prompt }) }),
  requestChange: (projectId: number, prompt: string) =>
    request<Build>(`/api/projects/${projectId}/builds`, {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  cancelBuild: (id: number) => request<Build>(`/api/builds/${id}/cancel`, { method: "POST" }),
  /** Follow a build's log. Replays saved lines after `after`, then streams live ones. */
  followBuild: (id: number, after: number, onEvent: (e: LogEvent) => void, signal: AbortSignal) =>
    readSSE<LogEvent>(`/api/builds/${id}/events?after=${after}`, onEvent, signal),
};
