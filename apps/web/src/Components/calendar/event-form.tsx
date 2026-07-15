import {
  attention_class_labels,
  attention_class_options,
  event_type_labels,
  event_type_options,
} from "../../lib/dispatch-maps/labels";
import { SelectField, TextAreaField, TextField } from "../ui/field";
import type { EventDraft } from "./event-draft";

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

function TimesRow({ draft, errors, on_change }: FieldsProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <TextField
        label="Starts"
        type="datetime-local"
        value={draft.start_local}
        error={errors["start_at"]}
        onChange={(event) => on_change({ start_local: event.target.value })}
      />
      <TextField
        label="Ends"
        type="datetime-local"
        value={draft.end_local}
        error={errors["end_at"]}
        onChange={(event) => on_change({ end_local: event.target.value })}
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
      <TimesRow {...props} />
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
