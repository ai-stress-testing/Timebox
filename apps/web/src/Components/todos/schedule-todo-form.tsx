import { useState } from "react";
import type {
  EventTypeCreate,
  EventTypeSummary,
  Todo,
  TodoScheduleRequest,
} from "../../lib/api-schemas";
import { todo_schedule_request_schema } from "../../lib/api-schemas";
import {
  attention_class_labels,
  attention_class_options,
} from "../../lib/dispatch-maps/labels";
import { compose_local_iso, date_input_value, next_full_hour, time_input_value } from "../../lib/time";
import { EventTypeField } from "../calendar/event-type-field";
import { Button } from "../ui/button";
import { SelectField, TextField } from "../ui/field";

const default_duration_minutes = 30;

function default_draft(todo: Todo, default_event_type: string) {
  const start = next_full_hour(new Date());
  const duration = todo.estimated_minutes ?? default_duration_minutes;
  const end = new Date(start.getTime() + duration * 60_000);
  return {
    date_local: date_input_value(start.toISOString()),
    start_time: time_input_value(start.toISOString()),
    end_time: time_input_value(end.toISOString()),
    event_type: default_event_type,
    attention_class: "active" as NonNullable<TodoScheduleRequest["attention_class"]>,
  };
}

type ScheduleTodoFormProps = {
  todo: Todo;
  event_types: EventTypeSummary[];
  on_create_type: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
  on_submit: (payload: TodoScheduleRequest) => void;
  on_cancel: () => void;
  busy: boolean;
};

export function ScheduleTodoForm({
  todo,
  event_types,
  on_create_type,
  on_submit,
  on_cancel,
  busy,
}: ScheduleTodoFormProps) {
  const [draft, set_draft] = useState(() =>
    default_draft(todo, event_types[0]?.key ?? "task"),
  );
  const [error, set_error] = useState<string | null>(null);
  const patch = (value: Partial<typeof draft>) =>
    set_draft((current) => ({ ...current, ...value }));

  const handle_submit = () => {
    const candidate = {
      start_at: compose_local_iso(draft.date_local, draft.start_time),
      end_at: compose_local_iso(draft.date_local, draft.end_time),
      event_type: draft.event_type,
      attention_class: draft.attention_class,
    };
    const parsed = todo_schedule_request_schema.safeParse(candidate);
    if (!parsed.success) {
      set_error(parsed.error.issues[0]?.message ?? "Check the fields.");
      return;
    }
    set_error(null);
    on_submit(parsed.data);
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge bg-surface-1 p-4">
      <TextField
        label="Date"
        type="date"
        value={draft.date_local}
        onChange={(event) => patch({ date_local: event.target.value })}
      />
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label="Starts"
          type="time"
          value={draft.start_time}
          onChange={(event) => patch({ start_time: event.target.value })}
        />
        <TextField
          label="Ends"
          type="time"
          value={draft.end_time}
          onChange={(event) => patch({ end_time: event.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <EventTypeField
          value={draft.event_type}
          event_types={event_types}
          on_change={(event_type) => patch({ event_type })}
          on_create_type={on_create_type}
        />
        <SelectField
          label="Attention"
          value={draft.attention_class}
          onChange={(event) =>
            patch({
              attention_class: event.target.value as TodoScheduleFormAttentionClass,
            })
          }
        >
          {attention_class_options.map((option) => (
            <option key={option} value={option}>
              {attention_class_labels[option]}
            </option>
          ))}
        </SelectField>
      </div>
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <div className="flex justify-end gap-2">
        <Button variant="subtle" disabled={busy} onClick={on_cancel}>
          Cancel
        </Button>
        <Button variant="primary" disabled={busy} onClick={handle_submit}>
          {busy ? "Scheduling…" : "Schedule"}
        </Button>
      </div>
    </div>
  );
}

type TodoScheduleFormAttentionClass = NonNullable<TodoScheduleRequest["attention_class"]>;
