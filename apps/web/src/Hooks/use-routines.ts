import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request, api_request_empty } from "../Services/api-client";
import {
  routine_list_schema,
  routine_run_list_schema,
  routine_run_schema,
  routine_schedule_response_schema,
  routine_schema,
  routine_step_list_schema,
  routine_step_schema,
} from "../lib/api-schemas";
import type {
  RoutineAdvanceRequest,
  RoutineCreate,
  RoutinePatch,
  RoutineScheduleRequest,
  RoutineStepCreate,
  RoutineStepPatch,
} from "../lib/api-schemas";

const routines_key = ["routines"] as const;
const events_key = ["events"] as const;

function steps_key(routine_id: string) {
  return [...routines_key, routine_id, "steps"] as const;
}

function runs_key(routine_id: string) {
  return [...routines_key, routine_id, "runs"] as const;
}

/* ---------------------------------------------------------------- routines */

export function use_routines() {
  return useQuery({
    queryKey: routines_key,
    queryFn: () => api_request("/routines", routine_list_schema),
  });
}

function use_routines_invalidation() {
  const query_client = useQueryClient();
  return () => query_client.invalidateQueries({ queryKey: routines_key });
}

export function use_create_routine() {
  const invalidate = use_routines_invalidation();
  return useMutation({
    mutationFn: (body: RoutineCreate) =>
      api_request("/routines", routine_schema, { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_routine() {
  const invalidate = use_routines_invalidation();
  return useMutation({
    mutationFn: (input: { id: string; patch: RoutinePatch }) =>
      api_request(`/routines/${input.id}`, routine_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_routine() {
  const invalidate = use_routines_invalidation();
  return useMutation({
    mutationFn: (id: string) => api_request_empty(`/routines/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

/* ------------------------------------------------------------------- steps */

export function use_routine_steps(routine_id: string) {
  return useQuery({
    queryKey: steps_key(routine_id),
    queryFn: () => api_request(`/routines/${routine_id}/steps`, routine_step_list_schema),
    enabled: routine_id.length > 0,
  });
}

function use_steps_invalidation(routine_id: string) {
  const query_client = useQueryClient();
  return () => {
    void query_client.invalidateQueries({ queryKey: steps_key(routine_id) });
    // Card totals (step_count / derived estimated_minutes) live on the routine.
    void query_client.invalidateQueries({ queryKey: routines_key });
  };
}

export function use_add_step(routine_id: string) {
  const invalidate = use_steps_invalidation(routine_id);
  return useMutation({
    mutationFn: (body: RoutineStepCreate) =>
      api_request(`/routines/${routine_id}/steps`, routine_step_schema, {
        method: "POST",
        body,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_update_step(routine_id: string) {
  const invalidate = use_steps_invalidation(routine_id);
  return useMutation({
    mutationFn: (input: { step_id: string; patch: RoutineStepPatch }) =>
      api_request(`/routines/${routine_id}/steps/${input.step_id}`, routine_step_schema, {
        method: "PATCH",
        body: input.patch,
      }),
    onSuccess: () => invalidate(),
  });
}

export function use_delete_step(routine_id: string) {
  const invalidate = use_steps_invalidation(routine_id);
  return useMutation({
    mutationFn: (step_id: string) =>
      api_request_empty(`/routines/${routine_id}/steps/${step_id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

export function use_reorder_steps(routine_id: string) {
  const invalidate = use_steps_invalidation(routine_id);
  return useMutation({
    mutationFn: (ordered_step_ids: string[]) =>
      api_request(`/routines/${routine_id}/steps/reorder`, routine_step_list_schema, {
        method: "POST",
        body: { ordered_step_ids },
      }),
    onSuccess: () => invalidate(),
  });
}

/* --------------------------------------------------------------------- runs */

export function use_routine_runs(routine_id: string) {
  return useQuery({
    queryKey: runs_key(routine_id),
    queryFn: () => api_request(`/routines/${routine_id}/runs`, routine_run_list_schema),
    enabled: routine_id.length > 0,
  });
}

function use_runs_invalidation(routine_id: string) {
  const query_client = useQueryClient();
  return () => void query_client.invalidateQueries({ queryKey: runs_key(routine_id) });
}

/** Starts a run for a routine — navigates to the run view on success. */
export function use_start_run(routine_id: string) {
  const invalidate = use_runs_invalidation(routine_id);
  return useMutation({
    mutationFn: () =>
      api_request(`/routines/${routine_id}/runs`, routine_run_schema, { method: "POST" }),
    onSuccess: () => invalidate(),
  });
}

export function use_advance_step() {
  return useMutation({
    mutationFn: (input: {
      run_id: string;
      step_run_id: string;
      payload: RoutineAdvanceRequest;
    }) =>
      api_request(
        `/runs/${input.run_id}/steps/${input.step_run_id}/advance`,
        routine_run_schema,
        { method: "POST", body: input.payload },
      ),
  });
}

export function use_finish_run() {
  return useMutation({
    mutationFn: (run_id: string) =>
      api_request(`/runs/${run_id}/finish`, routine_run_schema, { method: "POST" }),
  });
}

export function use_abandon_run() {
  return useMutation({
    mutationFn: (run_id: string) =>
      api_request(`/runs/${run_id}/abandon`, routine_run_schema, { method: "POST" }),
  });
}

/* ---------------------------------------------------------- schedule funnel */

export function use_schedule_routine(routine_id: string) {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: (payload: RoutineScheduleRequest) =>
      api_request(`/routines/${routine_id}/schedule`, routine_schedule_response_schema, {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      void query_client.invalidateQueries({ queryKey: routines_key });
      void query_client.invalidateQueries({ queryKey: events_key });
    },
  });
}
