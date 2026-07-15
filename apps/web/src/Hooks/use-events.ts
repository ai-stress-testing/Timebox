import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import { event_list_schema, event_schema } from "../lib/api-schemas";
import type { EventCreate, EventPatch } from "../lib/api-schemas";

const events_key = ["events"] as const;

export function use_events_range(start_iso: string, end_iso: string) {
  const search = new URLSearchParams({ start: start_iso, end: end_iso });
  return useQuery({
    queryKey: [...events_key, start_iso, end_iso],
    queryFn: () => api_request(`/events?${search}`, event_list_schema),
  });
}

function use_events_invalidation() {
  const query_client = useQueryClient();
  return () => query_client.invalidateQueries({ queryKey: events_key });
}

export function use_create_event() {
  const invalidate = use_events_invalidation();
  return useMutation({
    mutationFn: (body: EventCreate) =>
      api_request("/events", event_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_event() {
  const invalidate = use_events_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: EventPatch }) =>
      api_request(`/events/${input.id}`, event_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export type DeleteScope = "all" | "occurrence" | "following";
export type DeleteEventInput = {
  id: string;
  scope?: DeleteScope;
  occurrence_date?: string | null;
};

function delete_event_path({ id, scope = "all", occurrence_date }: DeleteEventInput): string {
  if (scope === "all") return `/events/${id}`;
  const search = new URLSearchParams({ scope });
  if (occurrence_date) search.set("occurrence_date", occurrence_date);
  return `/events/${id}?${search}`;
}

export function use_delete_event() {
  const invalidate = use_events_invalidation();
  return useMutation({
    mutationFn: (input: DeleteEventInput) =>
      api_request_empty(delete_event_path(input), { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}
