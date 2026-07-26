import { useState } from "react";
import type {
  LlmProviderKind,
  LlmSettingsIn,
  LlmSettingsOut,
} from "../../lib/api-schemas";
import { llm_settings_in_schema } from "../../lib/api-schemas";
import {
  llm_provider_base_url_placeholders,
  llm_provider_kind_labels,
  llm_provider_kind_options,
} from "../../lib/dispatch-maps/labels";
import { Button } from "../ui/button";
import { SelectField, TextField } from "../ui/field";

type Draft = {
  provider_kind: LlmProviderKind;
  base_url: string;
  model: string;
  api_key: string;
};

function to_draft(current: LlmSettingsOut): Draft {
  return {
    provider_kind: current.provider_kind,
    base_url: current.base_url,
    model: current.model,
    api_key: "",
  };
}

/** Empty api_key is omitted, not sent as "" — the server keeps the stored key. */
function build_payload(draft: Draft): LlmSettingsIn | null {
  const candidate = {
    provider_kind: draft.provider_kind,
    base_url: draft.base_url.trim(),
    model: draft.model.trim(),
    ...(draft.api_key === "" ? {} : { api_key: draft.api_key }),
  };
  const parsed = llm_settings_in_schema.safeParse(candidate);
  return parsed.success ? parsed.data : null;
}

type FieldsProps = {
  draft: Draft;
  has_api_key: boolean;
  on_change: (patch: Partial<Draft>) => void;
};

function ProviderFields({ draft, has_api_key, on_change }: FieldsProps) {
  const key_placeholder = has_api_key
    ? "•••• set — leave blank to keep it"
    : "Optional";
  return (
    <>
      <SelectField
        label="Provider"
        value={draft.provider_kind}
        onChange={(event) =>
          on_change({ provider_kind: event.target.value as LlmProviderKind })
        }
      >
        {llm_provider_kind_options.map((option) => (
          <option key={option} value={option}>
            {llm_provider_kind_labels[option]}
          </option>
        ))}
      </SelectField>
      <TextField
        label="Base URL"
        value={draft.base_url}
        placeholder={llm_provider_base_url_placeholders[draft.provider_kind]}
        onChange={(event) => on_change({ base_url: event.target.value })}
      />
      <TextField
        label="Model"
        value={draft.model}
        placeholder="e.g. qwen3, gemma-3"
        onChange={(event) => on_change({ model: event.target.value })}
      />
      <TextField
        label="API key"
        type="password"
        value={draft.api_key}
        placeholder={key_placeholder}
        onChange={(event) => on_change({ api_key: event.target.value })}
      />
    </>
  );
}

type FormProps = {
  current: LlmSettingsOut;
  on_submit: (payload: LlmSettingsIn) => void;
  busy: boolean;
};

export function LlmSettingsForm({ current, on_submit, busy }: FormProps) {
  const [draft, set_draft] = useState<Draft>(() => to_draft(current));
  const [error, set_error] = useState<string | null>(null);
  const patch = (value: Partial<Draft>) =>
    set_draft((prev) => ({ ...prev, ...value }));

  const handle_submit = () => {
    const payload = build_payload(draft);
    if (payload === null) {
      set_error("Check the provider, base URL, and model.");
      return;
    }
    set_error(null);
    on_submit(payload);
    patch({ api_key: "" });
  };

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-edge bg-surface-1 p-5">
      <h3 className="font-display font-bold text-hi">AI provider</h3>
      <ProviderFields draft={draft} has_api_key={current.has_api_key} on_change={patch} />
      {error ? (
        <p role="alert" className="text-sm text-danger">{error}</p>
      ) : null}
      <Button variant="primary" disabled={busy} onClick={handle_submit}>
        {busy ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
