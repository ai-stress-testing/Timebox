import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api_request } from "../Services/api-client";
import {
  pomodoro_finish_schema,
  pomodoro_session_schema,
  prompt_respond_schema,
  residual_prompt_list_schema,
} from "../lib/api-schemas";
import type { PromptResponseBody } from "../lib/dispatch-maps/prompt-responses";

const prompts_key = ["pomodoro", "prompts"] as const;

export function use_start_session() {
  return useMutation({
    mutationFn: (body: { event_id: string; intended_minutes: number }) =>
      api_request("/pomodoro/sessions", pomodoro_session_schema, {
        method: "POST",
        body,
      }),
  });
}

export type FinishSessionInput = {
  session_id: string;
  completion_flag: boolean;
  meaningful_minutes?: number;
  notes?: string;
};

export function use_finish_session() {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: ({ session_id, ...body }: FinishSessionInput) =>
      api_request(
        `/pomodoro/sessions/${session_id}/finish`,
        pomodoro_finish_schema,
        { method: "POST", body },
      ),
    onSuccess: () => {
      void query_client.invalidateQueries({ queryKey: prompts_key });
      void query_client.invalidateQueries({ queryKey: ["events"] });
    },
  });
}

export function use_pending_prompts() {
  return useQuery({
    queryKey: prompts_key,
    queryFn: () =>
      api_request(
        "/pomodoro/prompts?status=pending",
        residual_prompt_list_schema,
      ),
  });
}

export function use_respond_prompt() {
  const query_client = useQueryClient();
  return useMutation({
    mutationFn: (input: { prompt_id: string; body: PromptResponseBody }) =>
      api_request(
        `/pomodoro/prompts/${input.prompt_id}/respond`,
        prompt_respond_schema,
        { method: "POST", body: input.body },
      ),
    onSuccess: () => {
      void query_client.invalidateQueries({ queryKey: prompts_key });
      void query_client.invalidateQueries({ queryKey: ["events"] });
    },
  });
}
