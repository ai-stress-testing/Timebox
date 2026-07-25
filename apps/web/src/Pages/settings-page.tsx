import { EventTypesManager } from "../Components/settings/event-types-manager";
import { LlmSettingsForm } from "../Components/settings/llm-settings-form";
import { use_llm_settings, use_save_llm_settings } from "../Hooks/use-ai";
import type { LlmSettingsIn } from "../lib/api-schemas";
import { to_error_message } from "../Services/api-client";
import { push_toast } from "../Store/toast-store";

export function SettingsPage() {
  const settings = use_llm_settings();
  const save = use_save_llm_settings();

  const handle_save = (payload: LlmSettingsIn) => {
    save.mutate(payload, {
      onSuccess: () => push_toast("AI provider settings saved.", "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  return (
    <section aria-label="Settings" className="mx-auto flex max-w-xl flex-col gap-6">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">Settings</h2>
      <p className="text-sm text-mid">
        Pick the local LLM runtime the AI timebox drawer talks to — Ollama, LM
        Studio, or any OpenAI-compatible endpoint. Nothing leaves this machine.
      </p>
      {settings.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(settings.error)}</p>
      ) : null}
      {settings.data ? (
        <LlmSettingsForm current={settings.data} on_submit={handle_save} busy={save.isPending} />
      ) : null}
      <EventTypesManager />
    </section>
  );
}
