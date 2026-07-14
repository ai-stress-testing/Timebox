import type { Chore } from "../../lib/api-schemas";
import { attention_class_labels } from "../../lib/dispatch-maps/labels";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

type ChoreListProps = {
  chores: Chore[];
  on_delete: (id: string) => void;
  busy: boolean;
};

function ChoreRow({ chore, on_delete, busy }: {
  chore: Chore;
  on_delete: (id: string) => void;
  busy: boolean;
}) {
  return (
    <li
      className="flex items-center justify-between gap-3 rounded-md border
        border-edge bg-surface-2 px-4 py-3 transition-all
        duration-(--tb-dur-fast) hover:border-edge-strong"
    >
      <div className="min-w-0">
        <p className="truncate font-semibold text-hi">{chore.name}</p>
        <p className="text-xs text-mid">
          {chore.estimated_minutes} min · every {chore.n_current} days · priority {chore.priority}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge>{attention_class_labels[chore.attention_class]}</Badge>
        <Button
          variant="danger"
          disabled={busy}
          aria-label={`Delete chore ${chore.name}`}
          onClick={() => on_delete(chore.id)}
        >
          ✕
        </Button>
      </div>
    </li>
  );
}

export function ChoreList({ chores, on_delete, busy }: ChoreListProps) {
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
        <ChoreRow key={chore.id} chore={chore} on_delete={on_delete} busy={busy} />
      ))}
    </ul>
  );
}
