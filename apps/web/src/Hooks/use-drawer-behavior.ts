import { useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, RefObject } from "react";

const focusable_selector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

function wrap_tab_focus(
  panel: HTMLElement,
  event: ReactKeyboardEvent<HTMLElement>,
): void {
  const focusables = panel.querySelectorAll<HTMLElement>(focusable_selector);
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (!first || !last) return;
  const active = document.activeElement;
  if (event.shiftKey && (active === first || active === panel)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

export type DrawerBehavior = {
  panel_ref: RefObject<HTMLDivElement | null>;
  handle_keydown: (event: ReactKeyboardEvent<HTMLElement>) => void;
};

/** Keyboard behavior for modal drawers: focus on open, Esc close, Tab trap. */
export function use_drawer_behavior(on_close: () => void): DrawerBehavior {
  const panel_ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const previously_focused = document.activeElement;
    panel_ref.current?.focus();
    return () => {
      if (previously_focused instanceof HTMLElement) previously_focused.focus();
    };
  }, []);
  const handle_keydown = (event: ReactKeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      on_close();
    }
    if (event.key === "Tab" && panel_ref.current) {
      wrap_tab_focus(panel_ref.current, event);
    }
  };
  return { panel_ref, handle_keydown };
}
