import {
  attention_class_labels,
  attention_class_options,
  event_type_labels,
  event_type_options,
} from "../../lib/dispatch-maps/labels";
import { CheckboxField, SelectField, TextAreaField, TextField } from "../ui/field";
import type { EventDraft } from "./event-draft";
import { WeekdayToggles } from "./weekday-toggles";

type FieldsProps = {
  draft: EventDraft;
  errors: Record<string, string>;
  on_change: (patch: Partial<EventDraft>) => void;
};

function TypeAttentionRow({ draft, on_change }: FieldsProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <SelectField
        label="Type"
        value={draft.event_type}
        onChange={(event) =>
          on_change({
            event_type: event.target.value as EventDraft["event_type"],
          })
        }
      >
        {event_type_options.map((option) => (
          <option key={option} value={option}>
            {event_type_labels[option]}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Attention"
        value={draft.attention_class}
        onChange={(event) =>
          on_change({
            attention_class: event.target
              .value as EventDraft["attention_class"],
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
  );
}

function DateRow({ draft, errors, on_change }: FieldsProps) {
  return (
    <TextField
      label="Date"
      type="date"
      value={draft.date_local}
      error={errors["date_local"]}
      onChange={(event) => on_change({ date_local: event.target.value })}
    />
  );
}

function AllDayRow({ draft, on_change }: FieldsProps) {
  return (
    <CheckboxField
      label="All day"
      checked={draft.is_all_day}
      onChange={(event) => on_change({ is_all_day: event.target.checked })}
    />
  );
}

function TimesRow({ draft, errors, on_change }: FieldsProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <TextField
        label="Starts"
        type="time"
        value={draft.start_time}
        error={errors["start_time"]}
        onChange={(event) => on_change({ start_time: event.target.value })}
      />
      <TextField
        label="Ends"
        type="time"
        value={draft.end_time}
        error={errors["end_time"]}
        onChange={(event) => on_change({ end_time: event.target.value })}
      />
    </div>
  );
}

function RepeatsRow({ draft, on_change }: FieldsProps) {
  return (
    <CheckboxField
      label="Repeats weekly"
      checked={draft.repeats}
      onChange={(event) => on_change({ repeats: event.target.checked })}
    />
  );
}

function RepeatsDetail({ draft, errors, on_change }: FieldsProps) {
  const toggle_weekday = (value: number) => {
    const has_day = draft.repeat_weekdays.includes(value);
    const next = has_day
      ? draft.repeat_weekdays.filter((day) => day !== value)
      : [...draft.repeat_weekdays, value];
    on_change({ repeat_weekdays: next });
  };
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-edge p-3">
      <WeekdayToggles
        label="Repeats on"
        selected={draft.repeat_weekdays}
        on_toggle={toggle_weekday}
      />
      {errors["repeat_weekdays"] ? (
        <p role="alert" className="text-xs text-danger">{errors["repeat_weekdays"]}</p>
      ) : null}
      <TextField
        label="Until (optional)"
        type="date"
        value={draft.repeat_until}
        error={errors["repeat_until"]}
        onChange={(event) => on_change({ repeat_until: event.target.value })}
      />
    </div>
  );
}

/** The shared field set for create + edit event drawers. */
export function EventFormFields(props: FieldsProps) {
  const { draft, errors, on_change } = props;
  return (
    <div className="flex flex-col gap-4">
      <TextField
        label="Title"
        value={draft.title}
        error={errors["title"]}
        placeholder="What are you timeboxing?"
        onChange={(event) => on_change({ title: event.target.value })}
      />
      <TypeAttentionRow {...props} />
      <DateRow {...props} />
      <AllDayRow {...props} />
      {draft.is_all_day ? null : <TimesRow {...props} />}
      <RepeatsRow {...props} />
      {draft.repeats ? <RepeatsDetail {...props} /> : null}
      <TextField
        label="Estimated minutes"
        type="number"
        min={1}
        value={draft.estimated_minutes}
        error={errors["estimated_minutes"]}
        placeholder="Optional"
        onChange={(event) =>
          on_change({ estimated_minutes: event.target.value })
        }
      />
      <TextAreaField
        label="Description"
        value={draft.description}
        placeholder="Optional"
        onChange={(event) => on_change({ description: event.target.value })}
      />
    </div>
  );
}
