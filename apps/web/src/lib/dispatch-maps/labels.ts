import type {
  AttentionClass,
  EventStatus,
  EventType,
  LlmProviderKind,
} from "../api-schemas";
import {
  attention_class_schema,
  calendar_color_schema,
  event_status_schema,
  event_type_schema,
  llm_provider_kind_schema,
} from "../api-schemas";

export const event_type_labels: Record<EventType, string> = {
  meeting: "Meeting",
  task: "Task",
  personal: "Personal",
  chore: "Chore",
  homework: "Homework",
  passive: "Passive",
  physical: "Physical",
};

export const attention_class_labels: Record<AttentionClass, string> = {
  active: "Active",
  involved: "Involved",
  passive: "Passive",
};

export const event_status_labels: Record<EventStatus, string> = {
  scheduled: "Scheduled",
  in_progress: "In progress",
  completed: "Completed",
  skipped: "Skipped",
  cancelled: "Cancelled",
};

export const llm_provider_kind_labels: Record<LlmProviderKind, string> = {
  ollama: "Ollama",
  openai_compat: "OpenAI-compatible (LM Studio, etc.)",
};

export const llm_provider_base_url_placeholders: Record<LlmProviderKind, string> = {
  ollama: "http://localhost:11434",
  openai_compat: "http://localhost:1234",
};

export const event_type_options = event_type_schema.options;
export const attention_class_options = attention_class_schema.options;
export const event_status_options = event_status_schema.options;
export const calendar_color_options = calendar_color_schema.options;
export const llm_provider_kind_options = llm_provider_kind_schema.options;

/** 0=Sun .. 6=Sat, per the contract's preferred_days/avoid_days. */
export const weekday_options: ReadonlyArray<{ value: number; label: string }> = [
  { value: 0, label: "Sun" },
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
];
