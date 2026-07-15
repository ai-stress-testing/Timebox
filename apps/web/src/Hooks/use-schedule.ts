import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request } from "../Services/api-client";
import {
  schedule_apply_schema,
  schedule_run_detail_schema,
  schedule_run_list_schema,
} from "../lib/api-schemas";
import type { ScheduleRunCreate } from "../lib/api-schemas";

const runs_key = ["schedule", "runs"] as const;

export function use_schedule_runs(limit = 10) {
  return useQuery({
    queryKey: [...runs_key, limit],
    queryFn: () =>
      api_request(`/schedule/runs?limit=${limit}`, schedule_run_list_schema),
  });
}

export function use_run_detail(run_id: string | null) {
  return useQuery({
    queryKey: [...runs_key, "detail", run_id],
    queryFn: () =>
      api_request(`/schedule/runs/${run_id}`, schedule_run_detail_schema),
    enabled: run_id !== null,
  });
}

export function use_create_run() {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: (body: ScheduleRunCreate) =>
      api_request("/schedule/runs", schedule_run_detail_schema, {
        method: "POST",
        body,
      }),
    onSuccess: (detail) => {
      query_client.setQueryData([...runs_key, "detail", detail.id], detail);
      void query_client.invalidateQueries({ queryKey: runs_key });
    },
  });
}

export function use_apply_run() {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: (run_id: string) =>
      api_request(`/schedule/runs/${run_id}/apply`, schedule_apply_schema, {
        method: "POST",
      }),
    onSuccess: () => {
      void query_client.invalidateQueries({ queryKey: ["events"] });
      void query_client.invalidateQueries({ queryKey: runs_key });
    },
  });
}
