import { useState } from "react";
import type { EventTypeCreate, EventTypeSummary, RoutineRun } from "../lib/api-schemas";
import { RoutineForm } from "../Components/routines/routine-form";
import { RoutineList } from "../Components/routines/routine-list";
import { RoutineRunView } from "../Components/routines/routine-run-view";
import { use_create_event_type, use_event_types } from "../Hooks/use-event-types";
import { use_create_routine, use_routines } from "../Hooks/use-routines";
import { to_error_message } from "../Services/api-client";
import { push_toast } from "../Store/toast-store";

/** Only active types are selectable when scheduling a routine onto the calendar. */
function active_types(types: EventTypeSummary[] | undefined): EventTypeSummary[] {
  return (types ?? []).filter((type) => type.is_active);
}

/** Routines page: a card grid (RoutineList) that swaps for a focused
 * RoutineRunView while a run is in progress — not wired into the app's page
 * dispatch map yet (see the final report for the PageKey/nav snippet). */
export function RoutinesPage() {
  const routines = use_routines();
  const create = use_create_routine();
  const types = use_event_types();
  const create_type = use_create_event_type();

  const [active_run, set_active_run] = useState<RoutineRun | null>(null);
  const [active_routine_name, set_active_routine_name] = useState<string>("");

  const handle_create = (routine: Parameters<typeof create.mutate>[0]) => {
    create.mutate(routine, {
      onSuccess: () => push_toast("Routine added.", "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_create_type = async (
    payload: EventTypeCreate,
  ): Promise<EventTypeSummary | null> => {
    try {
      const created = await create_type.mutateAsync(payload);
      push_toast(`Type "${created.label}" created.`, "ok");
      return created;
    } catch (cause) {
      push_toast(to_error_message(cause), "danger");
      return null;
    }
  };

  if (active_run) {
    return (
      <section aria-label="Routine run" className="flex flex-col gap-6">
        <RoutineRunView
          run={active_run}
          routine_name={active_routine_name}
          on_run_updated={(run) => set_active_run(run)}
          on_exit={() => set_active_run(null)}
        />
      </section>
    );
  }

  return (
    <section aria-label="Routines" className="flex flex-col gap-6">
      <h2 className="font-display text-title tracking-hug font-bold text-hi">Routines</h2>
      {routines.isError ? (
        <p role="alert" className="text-sm text-danger">{to_error_message(routines.error)}</p>
      ) : null}
      <RoutineList
        routines={routines.data ?? []}
        event_types={active_types(types.data)}
        on_create_type={handle_create_type}
        on_run_started={(run) => {
          const routine = (routines.data ?? []).find((candidate) => candidate.id === run.routine_id);
          set_active_routine_name(routine?.name ?? "Routine");
          set_active_run(run);
        }}
      />
      <RoutineForm on_submit={handle_create} busy={create.isPending} />
    </section>
  );
}
