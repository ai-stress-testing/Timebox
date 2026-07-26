import { ChoreForm } from "../Components/chores/chore-form";
import { ChoreList } from "../Components/chores/chore-list";
import { PlanPanel } from "../Components/chores/plan-panel";
import {
  use_chores,
  use_complete_chore,
  use_create_chore,
  use_delete_chore,
  use_update_chore,
} from "../Hooks/use-chores";
import { to_error_message } from "../Services/api-client";
import { push_toast } from "../Store/toast-store";

export function ChoresPage() {
  const chores = use_chores();
  const create = use_create_chore();
  const remove = use_delete_chore();
  const update = use_update_chore();
  const complete = use_complete_chore();

  const handle_create = (chore: Parameters<typeof create.mutate>[0]) => {
    create.mutate(chore, {
      onSuccess: () => push_toast("Chore added.", "ok"),
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_delete = (id: string) => {
    remove.mutate(id, {
      onError: (cause) => push_toast(to_error_message(cause), "danger"),
    });
  };

  const handle_commit_n_current = (id: string, n_current: number) => {
    // The chore-patch API's field for the scheduled cadence is `n_days`
    // (see ChorePatch) even though it lands on ChoreDefinition.n_current.
    update.mutate(
      { id, patch: { n_days: n_current } },
      { onError: (cause) => push_toast(to_error_message(cause), "danger") },
    );
  };

  const handle_complete = (id: string) => {
    complete.mutate(
      { id },
      {
        onSuccess: () => push_toast("Chore marked done.", "ok"),
        onError: (cause) => push_toast(to_error_message(cause), "danger"),
      },
    );
  };

  return (
    <section aria-label="Chores" className="grid gap-6 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <h2 className="font-display text-title tracking-hug font-bold text-hi">Chores</h2>
        {chores.isError ? (
          <p role="alert" className="text-sm text-danger">{to_error_message(chores.error)}</p>
        ) : null}
        <ChoreList
          chores={chores.data ?? []}
          on_delete={handle_delete}
          on_commit_n_current={handle_commit_n_current}
          on_complete={handle_complete}
          busy={remove.isPending || update.isPending || complete.isPending}
        />
        <ChoreForm on_submit={handle_create} busy={create.isPending} />
      </div>
      <div className="flex flex-col gap-4">
        <h2 className="font-display text-title tracking-hug font-bold text-hi">Planner</h2>
        <PlanPanel />
      </div>
    </section>
  );
}
