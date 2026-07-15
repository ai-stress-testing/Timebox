import type { PromptResponseKind } from "../api-schemas";

export type PromptResponseBody = {
  response: PromptResponseKind;
  remaining_minutes?: number;
};

export type PromptActionSpec = {
  kind: PromptResponseKind;
  label: string;
  needs_minutes: boolean;
  tone: "primary" | "ghost" | "danger";
  build_body: (remaining_minutes: number | null) => PromptResponseBody | null;
};

/** Residual "Done?" prompt actions — dispatch map, order is display order. */
export const prompt_actions: readonly PromptActionSpec[] = [
  {
    kind: "completed",
    label: "Done — task finished",
    needs_minutes: false,
    tone: "primary",
    build_body: () => ({ response: "completed" }),
  },
  {
    kind: "confirmed",
    label: "Still remaining…",
    needs_minutes: true,
    tone: "ghost",
    build_body: (remaining_minutes) =>
      remaining_minutes && remaining_minutes > 0
        ? { response: "confirmed", remaining_minutes }
        : null,
  },
  {
    kind: "dismissed",
    label: "Dismiss",
    needs_minutes: false,
    tone: "danger",
    build_body: () => ({ response: "dismissed" }),
  },
];
