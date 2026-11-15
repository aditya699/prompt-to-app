// Server state lives in TanStack Query. Components never call `fetch` directly.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { ACTIVE_STATUSES } from "@/api/types";

export const keys = {
  health: ["health"] as const,
  examples: ["examples"] as const,
  projects: ["projects"] as const,
  project: (id: number) => ["projects", id] as const,
};

export function useHealth() {
  return useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: 5 * 60_000 });
}

export function useExamples() {
  return useQuery({ queryKey: keys.examples, queryFn: api.examples, staleTime: Infinity });
}

export function useProjects() {
  return useQuery({
    queryKey: keys.projects,
    queryFn: api.listProjects,
    // Poll while anything is building so the cards update on their own.
    refetchInterval: (query) =>
      query.state.data?.some((p) => p.latest_build && ACTIVE_STATUSES.includes(p.latest_build.status))
        ? 3000
        : false,
  });
}

export function useProject(id: number) {
  return useQuery({ queryKey: keys.project(id), queryFn: () => api.getProject(id) });
}

export function useCreateProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: (project) => {
      client.setQueryData(keys.project(project.id), project);
      client.invalidateQueries({ queryKey: keys.projects });
    },
  });
}

export function useRequestChange(projectId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (prompt: string) => api.requestChange(projectId, prompt),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.project(projectId) }),
  });
}

export function useCancelBuild(projectId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.cancelBuild,
    onSettled: () => client.invalidateQueries({ queryKey: keys.project(projectId) }),
  });
}

export function useDeleteProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.projects }),
  });
}
