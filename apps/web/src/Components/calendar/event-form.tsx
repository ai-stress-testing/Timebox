import {
  attention_class_labels,
  attention_class_options,
} from "../../lib/dispatch-maps/labels";
import type { EventTitleSuggestion, EventTypeCreate, EventTypeSummary } from "../../lib/api-schemas";
import { use_duration_profile_lookup } from "../../Hooks/use-duration-profiles";
import { CheckboxField, SelectField, TextAreaField, TextField } from "../ui/field";
import type { EventDraft } from "./event-draft";
import { EventTypeField } from "./event-type-field";
import { WeekdayToggles } from "./weekday-toggles";

type FieldsProps = {
  draft: EventDraft;
  errors: Record<string, string>;
  on_change: (patch: Partial<EventDraft>) => void;
  title_suggestions?: EventTitleSuggestion[];
  event_types?: EventTypeSummary[];
  on_create_type?: (payload: EventTypeCreate) => Promise<EventTypeSummary | null>;
};

const title_datalist_id = "event-title-options";

/** Typing a known title prefills estimated minutes with its learned average —
 * but only when that field is still empty, never overwriting real input. */
function title_change_patch(
  value: string,
  draft: EventDraft,
  suggestions: EventTitleSuggestion[],
): Partial<EventDraft> {
  const match = suggestions.find((suggestion) => suggestion.title === value);
  const can_prefill = match?.avg_minutes != null && draft.estimated_minutes.trim() === "";
  return can_prefill
    ? { title: value, estimated_minutes: String(match.avg_minutes) }
    : { title: value };
}

function TitleRow({ draft, errors, on_change, title_suggestions = [] }: FieldsProps) {
  const { data: duration_profile } = use_duration_profile_lookup(draft.title);
  return (
    <>
      <TextField
        label="Title"
        value={draft.title}
        error={errors["title"]}
        placeholder="What are you timeboxing?"
        list={title_datalist_id}
        autoComplete="off"
        onChange={(event) =>
          on_change(title_change_patch(event.target.value, draft, title_suggestions))
        }
      />
      {duration_profile && duration_profile.total_sample_count > 0 ? (
        <p className="text-xs text-mid">
          Usually takes ~{Math.round(duration_profile.total_mean)} min (from{" "}
          {duration_profile.total_sample_count} past completions)
        </p>
      ) : null}
      <datalist id={title_datalist_id}>
        {title_suggestions.map((suggestion) => (
          <option key={suggestion.title} value={suggestion.title} />
        ))}
      </datalist>
    </>
  );
}

async function no_create(): Promise<EventTypeSummary | null> {
  return null;
}

function TypeAttentionRow({
  draft,
  on_change,
  event_types = [],
  on_create_type = no_create,
}: FieldsProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <EventTypeField
        value={draft.event_type}
        event_types={event_types}
        on_change={(event_type) => on_change({ event_type })}
        on_create_type={on_create_type}
      />
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
      <TitleRow {...props} />
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
