import { useMutation, useQuery } from "@tanstack/react-query";
import { api_request } from "../Services/api-client";
import {
  ai_health_schema,
  timebox_response_schema,
} from "../lib/api-schemas";
import type { TimeboxRequest } from "../lib/api-schemas";
import { use_session_store } from "../Store/session-store";

const health_poll_interval_ms = 30_000;

export function use_ai_health() {
  const token = use_session_store((state) => state.token);
  return useQuery({
    queryKey: ["ai", "health"],
    queryFn: () => api_request("/ai/health", ai_health_schema),
    enabled: token !== null,
    refetchInterval: health_poll_interval_ms,
  });
}

export function use_timebox_proposal() {
  return useMutation({
    mutationFn: (body: TimeboxRequest) =>
      api_request("/ai/timebox", timebox_response_schema, {
        method: "POST",
        body,
      }),
  });
}
