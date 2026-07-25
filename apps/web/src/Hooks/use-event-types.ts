import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import {
  event_type_summary_list_schema,
  event_type_summary_schema,
} from "../lib/api-schemas";
import type { EventTypeCreate, EventTypePatch } from "../lib/api-schemas";

const event_types_key = ["event-types"] as const;
const events_key = ["events"] as const;

/** All of the user's event types (presets + custom), server-ordered. */
export function use_event_types() {
  return useQuery({
    queryKey: event_types_key,
    queryFn: () => api_request("/event-types", event_type_summary_list_schema),
  });
}

/** A create/patch/delete invalidates both the types list and cached events,
 * since an event's rendered color/label depends on its type. */
function use_event_types_invalidation() {
  const query_client = useQueryClient();
  return () => {
    void query_client.invalidateQueries({ queryKey: event_types_key });
    void query_client.invalidateQueries({ queryKey: events_key });
  };
}

export function use_create_event_type() {
  const invalidate = use_event_types_invalidation();
  return useMutation({
    mutationFn: (body: EventTypeCreate) =>
      api_request("/event-types", event_type_summary_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_event_type() {
  const invalidate = use_event_types_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: EventTypePatch }) =>
      api_request(`/event-types/${input.id}`, event_type_summary_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_event_type() {
  const invalidate = use_event_types_invalidation();
  return useMutation({
    mutationFn: (id: string) =>
      api_request_empty(`/event-types/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}
