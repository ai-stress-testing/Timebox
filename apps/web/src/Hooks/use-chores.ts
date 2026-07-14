import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import { chore_list_schema, chore_schema } from "../lib/api-schemas";
import type { ChoreCreate } from "../lib/api-schemas";

const chores_key = ["chores"] as const;

export function use_chores() {
  return useQuery({
    queryKey: chores_key,
    queryFn: () => api_request("/chores", chore_list_schema),
  });
}

function use_chores_invalidation() {
  const query_client = useQueryClient();
  return () => query_client.invalidateQueries({ queryKey: chores_key });
}

export function use_create_chore() {
  const invalidate = use_chores_invalidation();
  return useMutation({
    mutationFn: (body: ChoreCreate) =>
      api_request("/chores", chore_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_chore() {
  const invalidate = use_chores_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: Partial<ChoreCreate> }) =>
      api_request(`/chores/${input.id}`, chore_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_chore() {
  const invalidate = use_chores_invalidation();
  return useMutation({
    mutationFn: (id: string) =>
      api_request_empty(`/chores/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}
