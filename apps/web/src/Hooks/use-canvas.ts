import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import {
  canvas_alarm_schema,
  canvas_item_list_schema,
  canvas_item_schema,
} from "../lib/api-schemas";
import type {
  CanvasAlarmCreate,
  CanvasAlarmPatch,
  CanvasItemCreate,
  CanvasItemPatch,
} from "../lib/api-schemas";

const canvas_key = ["canvas"] as const;

export function use_canvas_items() {
  return useQuery({
    queryKey: canvas_key,
    queryFn: () => api_request("/canvas/items", canvas_item_list_schema),
    // Server-computed elapsed goes stale the instant it's fetched — the UI
    // ticks it locally; re-fetch periodically just to catch lazy status
    // flips (e.g. a timer that completed) and cross-tab changes.
    refetchInterval: 15_000,
  });
}

function use_canvas_invalidation() {
  const query_client = useQueryClient();
  return () => query_client.invalidateQueries({ queryKey: canvas_key });
}

export function use_create_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (body: CanvasItemCreate) =>
      api_request("/canvas/items", canvas_item_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: CanvasItemPatch }) =>
      api_request(`/canvas/items/${input.id}`, canvas_item_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_start_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (id: string) =>
      api_request(`/canvas/items/${id}/start`, canvas_item_schema, { method: "POST" }),
    onSuccess: () => invalidate(),
  });
}

export function use_pause_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (id: string) =>
      api_request(`/canvas/items/${id}/pause`, canvas_item_schema, { method: "POST" }),
    onSuccess: () => invalidate(),
  });
}

export function use_reset_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (id: string) =>
      api_request(`/canvas/items/${id}/reset`, canvas_item_schema, { method: "POST" }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_canvas_item() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (id: string) => api_request_empty(`/canvas/items/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

export function use_create_canvas_alarm() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (input: { item_id: string; body: CanvasAlarmCreate }) =>
      api_request(`/canvas/items/${input.item_id}/alarms`, canvas_alarm_schema, {
        method: "POST",
        body: input.body,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_patch_canvas_alarm() {
  const invalidate = use_canvas_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: CanvasAlarmPatch }) =>
      api_request(`/canvas/alarms/${input.id}`, canvas_alarm_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}
