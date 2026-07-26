import { use_ui_store } from "../../Store/ui-store";
import type { PageKey } from "../../Store/ui-store";
import { Button } from "../ui/button";
import { AiHealthDot } from "./ai-health-dot";

const nav_items: ReadonlyArray<{ key: PageKey; label: string }> = [
  { key: "calendar", label: "Calendar" },
  { key: "chores", label: "Chores" },
  { key: "focus", label: "Focus" },
  { key: "todo", label: "To do" },
  { key: "routines", label: "Routines" },
  { key: "canvas", label: "Canvas" },
];

function NavTabs() {
  const page = use_ui_store((state) => state.page);
  const set_page = use_ui_store((state) => state.set_page);
  return (
    <nav aria-label="Pages" className="flex gap-1 rounded-full border border-edge bg-surface-1 p-1">
      {nav_items.map((item) => {
        const is_active = item.key === page;
        const active_classes = is_active
          ? "[background:var(--tb-gradient-accent)] text-accent-ink shadow-glow-soft"
          : "text-mid hover:bg-surface-2 hover:text-hi";
        return (
          <button
            key={item.key}
            aria-current={is_active ? "page" : undefined}
            onClick={() => set_page(item.key)}
            className={`cursor-pointer rounded-full px-4 py-1.5 text-sm
              font-medium transition-all duration-(--tb-dur-fast)
              ease-spring ${active_classes}`}
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}

export function AppHeader() {
  const open_ai_drawer = use_ui_store((state) => state.open_ai_drawer);
  const page = use_ui_store((state) => state.page);
  const set_page = use_ui_store((state) => state.set_page);
  return (
    <header
      className="sticky top-0 z-40 flex h-(--tb-header-height) items-center
        justify-between gap-3 border-b border-edge bg-surface-0/80 px-4
        backdrop-blur-md sm:px-6"
    >
      <h1
        className="font-display tracking-hug bg-clip-text text-lg font-black
          text-transparent [background-image:var(--tb-gradient-accent)]"
      >
        Timebox
      </h1>
      <NavTabs />
      <div className="flex items-center gap-3">
        <AiHealthDot />
        <Button variant="primary" onClick={open_ai_drawer}>
          ✦ AI timebox
        </Button>
        <Button
          variant="subtle"
          onClick={() => set_page("settings")}
          aria-label="AI provider settings"
          aria-current={page === "settings" ? "page" : undefined}
        >
          ⚙
        </Button>
      </div>
    </header>
  );
}
