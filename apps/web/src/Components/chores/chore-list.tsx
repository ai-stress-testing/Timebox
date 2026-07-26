import type { Chore } from "../../lib/api-schemas";
import { attention_class_labels } from "../../lib/dispatch-maps/labels";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Slider } from "../ui/slider";

const FALLBACK_N_MIN = 1;
const FALLBACK_N_MAX = 30;

type ChoreListProps = {
  chores: Chore[];
  on_delete: (id: string) => void;
  on_commit_n_current: (id: string, n_current: number) => void;
  on_complete: (id: string) => void;
  busy: boolean;
};

function due_label(days_until_due: number | null): string | null {
  if (days_until_due === null) return null;
  if (days_until_due < 0) return `overdue by ${Math.abs(days_until_due)}d`;
  if (days_until_due === 0) return "due today";
  return `due in ${days_until_due}d`;
}

function ChoreRow({ chore, on_delete, on_commit_n_current, on_complete, busy }: {
  chore: Chore;
  on_delete: (id: string) => void;
  on_commit_n_current: (id: string, n_current: number) => void;
  on_complete: (id: string) => void;
  busy: boolean;
}) {
  const n_min = chore.n_min ?? FALLBACK_N_MIN;
  const n_max = chore.n_max ?? FALLBACK_N_MAX;
  const slider_default = chore.recommended_n ?? chore.n_current;
  const due = due_label(chore.days_until_due);

  return (
    <li
      className="flex flex-col gap-3 rounded-md border border-edge bg-surface-2
        px-4 py-3 transition-all duration-(--tb-dur-fast) hover:border-edge-strong"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-hi">{chore.name}</p>
          <p className="text-xs text-mid">
            {chore.estimated_minutes} min · every {chore.n_current} days · priority {chore.priority}
            {due ? ` · ${due}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge>{attention_class_labels[chore.attention_class]}</Badge>
          <Button
            variant="ghost"
            disabled={busy}
            aria-label={`Mark ${chore.name} done`}
            onClick={() => on_complete(chore.id)}
          >
            Done
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            aria-label={`Delete chore ${chore.name}`}
            onClick={() => on_delete(chore.id)}
          >
            ✕
          </Button>
        </div>
      </div>
      <Slider
        label="Cadence"
        min={n_min}
        max={n_max}
        value={slider_default}
        onChange={() => {}}
        onCommit={(value) => on_commit_n_current(chore.id, value)}
      />
    </li>
  );
}

export function ChoreList({ chores, on_delete, on_commit_n_current, on_complete, busy }: ChoreListProps) {
  if (chores.length === 0) {
    return (
      <p className="rounded-md border border-edge bg-surface-1 p-6 text-center text-sm text-mid">
        No chores yet — add one, then let the Monte Carlo planner place it.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {chores.map((chore) => (
        <ChoreRow
          key={chore.id}
          chore={chore}
          on_delete={on_delete}
          on_commit_n_current={on_commit_n_current}
          on_complete={on_complete}
          busy={busy}
        />
      ))}
    </ul>
  );
}
