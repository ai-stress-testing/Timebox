import { useEffect, useState } from "react";

/** Current time, refreshed on `interval_ms` — a trailing clock, not a live one. */
export function use_now(interval_ms: number): Date {
  const [now, set_now] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => set_now(new Date()), interval_ms);
    return () => clearInterval(id);
  }, [interval_ms]);
  return now;
}
