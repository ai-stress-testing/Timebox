import { useQuery } from "@tanstack/react-query";
import { api_request } from "../Services/api-client";
import { duration_profile_schema } from "../lib/api-schemas";

/** Welford-learned running-average duration for a given event title, sourced
 * from real completions (`actual_minutes`). A 404 just means no profile has
 * been learned for this title yet — that's an expected outcome, not an
 * error, so retries are disabled and callers should treat `isError` as
 * "no hint available" rather than surface it. */
export function use_duration_profile_lookup(title: string) {
  return useQuery({
    queryKey: ["duration-profile", title],
    queryFn: () =>
      api_request(
        `/duration-profiles/lookup?title=${encodeURIComponent(title)}`,
        duration_profile_schema,
      ),
    enabled: title.trim().length > 0,
    retry: false,
  });
}
