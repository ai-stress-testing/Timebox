import { use_ai_health } from "../../Hooks/use-ai";

type DotState = "ok" | "down" | "unknown";

/* health state -> dot classes + label (dispatch map) */
const dot_specs: Record<DotState, { classes: string; label: string }> = {
  ok: { classes: "bg-ok shadow-glow-soft", label: "Ollama connected" },
  down: { classes: "bg-danger", label: "Ollama unreachable" },
  unknown: { classes: "bg-low", label: "Checking Ollama…" },
};

function to_dot_state(ok: boolean | undefined): DotState {
  if (ok === undefined) return "unknown";
  return ok ? "ok" : "down";
}

/** Tiny status dot in the header: is the local Ollama daemon reachable? */
export function AiHealthDot() {
  const health = use_ai_health();
  const spec = dot_specs[to_dot_state(health.data?.ok)];
  const model = health.data?.model ?? "";
  return (
    <span
      className="flex items-center gap-2 text-xs text-low"
      title={`${spec.label}${model ? ` · ${model}` : ""}`}
    >
      <span
        aria-hidden="true"
        className={`inline-block size-2 rounded-full transition-colors
          duration-(--tb-dur-base) ${spec.classes}`}
      />
      <span className="sr-only">{spec.label}</span>
      <span className="hidden font-mono sm:inline">{model}</span>
    </span>
  );
}
