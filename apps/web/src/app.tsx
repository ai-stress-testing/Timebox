import type { ComponentType } from "react";
import { AppHeader } from "./Components/layout/app-header";
import { TimeboxDrawer } from "./Components/ai/timebox-drawer";
import { ToastViewport } from "./Components/ui/toast-viewport";
import { CalendarPage } from "./Pages/calendar-page";
import { ChoresPage } from "./Pages/chores-page";
import { FocusPage } from "./Pages/focus-page";
import { SettingsPage } from "./Pages/settings-page";
import { TodoPage } from "./Pages/todo-page";
import { VaultPage } from "./Pages/vault-page";
import { use_session_store } from "./Store/session-store";
import { use_ui_store } from "./Store/ui-store";
import type { PageKey } from "./Store/ui-store";

/* page key -> page component (dispatch map, no router lib) */
const pages: Record<PageKey, ComponentType> = {
  calendar: CalendarPage,
  chores: ChoresPage,
  focus: FocusPage,
  todo: TodoPage,
  settings: SettingsPage,
};

function UnlockedApp() {
  const page = use_ui_store((state) => state.page);
  const ai_drawer_open = use_ui_store((state) => state.ai_drawer_open);
  const ActivePage = pages[page];
  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6">
        <ActivePage />
      </main>
      {ai_drawer_open ? <TimeboxDrawer /> : null}
    </div>
  );
}

export function App() {
  const token = use_session_store((state) => state.token);
  return (
    <>
      {token === null ? <VaultPage /> : <UnlockedApp />}
      <ToastViewport />
    </>
  );
}
