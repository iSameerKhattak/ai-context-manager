"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createApiClient } from "@/lib/api/client";

export function useApi() {
  const { getToken } = useAuth();
  const client = createApiClient(() => getToken({ template: "" }));
  const queryClient = useQueryClient();
  return { client, queryClient };
}

// ── Organizations ──────────────────────────────────────────────────

export function useMyOrgs() {
  const { client } = useApi();
  return useQuery({
    queryKey: ["orgs"],
    queryFn: () => client.fetchMyOrgs(),
  });
}

export function useCreateOrg() {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (data: { slug: string; name: string }) => client.createOrg(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orgs"] }),
  });
}

// ── Projects ───────────────────────────────────────────────────────

export function useProjects(orgId: string | null) {
  const { client } = useApi();
  return useQuery({
    queryKey: ["projects", orgId],
    queryFn: () => client.fetchProjects(orgId!),
    enabled: !!orgId,
  });
}

export function useCreateProject(orgId: string) {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (data: { slug: string; name: string; description?: string }) =>
      client.createProject(orgId, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["projects", orgId] }),
  });
}

// ── GitHub Integration ─────────────────────────────────────────────

export function useGitHubInstallUrl(orgSlug?: string) {
  const { client } = useApi();
  return useQuery({
    queryKey: ["github-install-url", orgSlug],
    queryFn: () => client.getGitHubInstallUrl(orgSlug),
    staleTime: 5 * 60 * 1000,
  });
}

export function useInstallations(orgId?: string) {
  const { client } = useApi();
  return useQuery({
    queryKey: ["github-installations", orgId],
    queryFn: () => client.listInstallations(orgId),
    enabled: !!orgId,
    staleTime: 2 * 60 * 1000,
  });
}

// ── Search ────────────────────────────────────────────────────────

export function useSearch() {
  const { client } = useApi();
  return useMutation({
    mutationFn: (data: { project_id: string; query: string; k?: number; mode?: string }) =>
      client.search(data),
  });
}

export function useSearchPreview() {
  const { client } = useApi();
  return useMutation({
    mutationFn: (data: { project_id: string; query: string; max_chunks?: number; mode?: string }) =>
      client.searchPreview(data),
  });
}

// ── Chat ──────────────────────────────────────────────────────────

export function useConversation(conversationId: string | null) {
  const { client } = useApi();
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => client.getConversation(conversationId!),
    enabled: !!conversationId,
  });
}

export function useCreateConversation() {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (projectId: string) => client.createConversation(projectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversation"] }),
  });
}

export function useSendMessage(conversationId: string | null) {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (data: { content: string; model?: string }) =>
      client.sendMessage(conversationId!, data.content, data.model),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
    },
  });
}

export function useDeleteConversation() {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (conversationId: string) => client.deleteConversation(conversationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversation"] }),
  });
}

// ── Memory ────────────────────────────────────────────────────────

export function useFacts(projectId: string | null, scope?: string) {
  const { client } = useApi();
  return useQuery({
    queryKey: ["facts", projectId, scope],
    queryFn: () => client.listFacts(projectId!, scope),
    enabled: !!projectId,
  });
}

export function useAssertFact() {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (data: { project_id: string; statement: string; scope?: string; confidence?: number }) =>
      client.assertFact(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["facts"] }),
  });
}

export function useDeleteFact() {
  const { client, queryClient } = useApi();
  return useMutation({
    mutationFn: (factId: string) => client.deleteFact(factId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["facts"] }),
  });
}
