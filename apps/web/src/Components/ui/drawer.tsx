import type { ReactNode } from "react";
import { use_drawer_behavior } from "../../Hooks/use-drawer-behavior";
import { Button } from "./button";

type DrawerProps = {
  title: string;
  on_close: () => void;
  children: ReactNode;
};

/**
 * Right-side modal drawer. Render conditionally (`open ? <Drawer/> : null`)
 * so mount/unmount drives focus restore and the entry animation.
 */
export function Drawer({ title, on_close, children }: DrawerProps) {
  const { panel_ref, handle_keydown } = use_drawer_behavior(on_close);
  return (
    <div className="fixed inset-0 z-50" onKeyDown={handle_keydown}>
      <div
        className="animate-fade-in absolute inset-0 bg-overlay backdrop-blur-xs"
        onClick={on_close}
        aria-hidden="true"
      />
      <div
        ref={panel_ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="animate-drawer-in absolute inset-y-0 right-0 w-full
          max-w-(--tb-drawer-width) overflow-y-auto border-l border-edge
          bg-surface-1 p-6 shadow-raised"
      >
        <header className="mb-5 flex items-center justify-between gap-4">
          <h2 className="font-display text-title tracking-hug font-bold text-hi">
            {title}
          </h2>
          <Button variant="subtle" aria-label="Close drawer" onClick={on_close}>
            <span aria-hidden="true">✕</span>
          </Button>
        </header>
        {children}
      </div>
    </div>
  );
}
