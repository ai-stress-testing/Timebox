import type { ReactNode } from "react";

type BadgeProps = { children: ReactNode; title?: string };

/** Small read-only pill, e.g. the server-assigned canvas_event_type. */
export function Badge({ children, title }: BadgeProps) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1 rounded-full border
        border-edge bg-surface-2 px-2 py-0.5 text-xs font-medium text-mid"
    >
      {children}
    </span>
  );
}
