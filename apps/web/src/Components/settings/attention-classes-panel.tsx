import { use_attention_classes } from "../../Hooks/use-attention-classes";
import type { AttentionClassMeta } from "../../lib/api-schemas";
import { to_error_message } from "../../Services/api-client";
import { Badge } from "../ui/badge";

function AttentionClassRow({ meta }: { meta: AttentionClassMeta }) {
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-edge bg-surface-1 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-hi">{meta.label}</span>
        {meta.pomodoro_applicable ? <Badge>Pomodoro</Badge> : null}
        {meta.residual_applicable ? <Badge>Residual carry-over</Badge> : null}
        <Badge>residual r: {meta.default_r}</Badge>
      </div>
      <p className="text-sm text-mid">{meta.description}</p>
    </li>
  );
}

function AttentionClassesList({ classes }: { classes: AttentionClassMeta[] }) {
  if (classes.length === 0) return <p className="text-sm text-mid">No attention classes found.</p>;
  return (
    <ul className="flex flex-col gap-2">
      {classes.map((meta) => (
        <AttentionClassRow key={meta.id} meta={meta} />
      ))}
    </ul>
  );
}

/** Settings section: read-only reference explaining how the app treats each
 * attention class (Active/Involved/Passive) — fixed, boot-seeded, never
 * user-editable. */
export function AttentionClassesPanel() {
  const classes = use_attention_classes();

  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-display font-bold text-hi">Attention classes</h3>
      {classes.isLoading ? <p className="text-sm text-mid">Loading attention classes…</p> : null}
      {classes.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(classes.error)}</p>
      ) : null}
      {classes.data ? <AttentionClassesList classes={classes.data} /> : null}
    </div>
  );
}
