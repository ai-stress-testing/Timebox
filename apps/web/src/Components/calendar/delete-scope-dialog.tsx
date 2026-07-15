import { use_drawer_behavior } from "../../Hooks/use-drawer-behavior";
import { Button } from "../ui/button";

export type DeleteScopeChoice = "occurrence" | "following";

type DeleteScopeDialogProps = {
  on_choose: (choice: DeleteScopeChoice) => void;
  on_cancel: () => void;
  busy: boolean;
};

/** "Delete vs delete this 1 event" — recurring events route through here
 * before the actual DELETE call (issue #4); non-recurring events skip it
 * and delete immediately (scope="all", see event-drawer.tsx). */
export function DeleteScopeDialog({ on_choose, on_cancel, busy }: DeleteScopeDialogProps) {
  const { panel_ref, handle_keydown } = use_drawer_behavior(on_cancel);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onKeyDown={handle_keydown}>
      <div
        className="animate-fade-in absolute inset-0 bg-overlay backdrop-blur-xs"
        onClick={on_cancel}
        aria-hidden="true"
      />
      <div
        ref={panel_ref}
        role="dialog"
        aria-modal="true"
        aria-label="Delete recurring event"
        tabIndex={-1}
        className="animate-drawer-in relative w-full max-w-sm rounded-2xl border
          border-edge bg-surface-1 p-6 shadow-raised"
      >
        <h3 className="font-display text-title tracking-hug font-bold text-hi">
          Delete this event?
        </h3>
        <p className="mt-1 text-sm text-mid">This event repeats. Choose what to delete.</p>
        <div className="mt-5 flex flex-col gap-2">
          <Button variant="danger" disabled={busy} onClick={() => on_choose("occurrence")}>
            This event
          </Button>
          <Button variant="danger" disabled={busy} onClick={() => on_choose("following")}>
            This and following events
          </Button>
          <Button variant="subtle" disabled={busy} onClick={on_cancel}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
