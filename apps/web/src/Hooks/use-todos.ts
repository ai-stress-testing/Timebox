import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import {
  batch_schedule_response_schema,
  todo_list_schema,
  todo_schema,
} from "../lib/api-schemas";
import type { BatchScheduleRequest, TodoCreate, TodoPatch } from "../lib/api-schemas";

const todos_key = ["todos"] as const;
const events_key = ["events"] as const;

export function use_todos() {
  return useQuery({
    queryKey: todos_key,
    queryFn: () => api_request("/todos", todo_list_schema),
  });
}

function use_todos_invalidation() {
  const query_client = useQueryClient();
  return () => query_client.invalidateQueries({ queryKey: todos_key });
}

export function use_create_todo() {
  const invalidate = use_todos_invalidation();
  return useMutation({
    mutationFn: (body: TodoCreate) =>
      api_request("/todos", todo_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_todo() {
  const invalidate = use_todos_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: TodoPatch }) =>
      api_request(`/todos/${input.id}`, todo_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_todo() {
  const invalidate = use_todos_invalidation();
  return useMutation({
    mutationFn: (id: string) => api_request_empty(`/todos/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

/** The funnel action (spec 015): schedules one or more todos in one request
 * — batch-schedule is the sole scheduling entry point now, even for a single
 * todo. Invalidates both the todos list (is_done flips server-side) and the
 * events cache (so the calendar picks up the newly created event(s)). */
export function use_batch_schedule() {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: (payload: BatchScheduleRequest) =>
      api_request("/todos/batch-schedule", batch_schedule_response_schema, {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      void query_client.invalidateQueries({ queryKey: todos_key });
      void query_client.invalidateQueries({ queryKey: events_key });
    },
  });
}
