import { useMutation, useQuery } from "@tanstack/react-query";
import {
  api_request,
  api_request_empty,
} from "../Services/api-client";
import {
  vault_generate_schema,
  vault_status_schema,
  vault_unlock_schema,
} from "../lib/api-schemas";
import type { Keyfile } from "../lib/api-schemas";
import { use_session_store } from "../Store/session-store";

export function use_vault_status() {
  return useQuery({
    queryKey: ["vault", "status"],
    queryFn: () => api_request("/vault/status", vault_status_schema),
  });
}

export function use_generate_key() {
  return useMutation({
    mutationFn: () =>
      api_request("/vault/generate", vault_generate_schema, {
        method: "POST",
      }),
  });
}

export function use_unlock() {
  const unlock = use_session_store((state) => state.unlock);
  return useMutation({
    mutationFn: (keyfile: Keyfile) =>
      api_request("/vault/unlock", vault_unlock_schema, {
        method: "POST",
        body: { keyfile },
      }),
    onSuccess: (session) => unlock(session),
  });
}

export function use_lock() {
  const lock = use_session_store((state) => state.lock);
  return useMutation({
    mutationFn: () => api_request_empty("/vault/lock", { method: "POST" }),
    onSettled: () => lock(),
  });
}
