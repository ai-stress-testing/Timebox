import { create } from "zustand";

/* UI-only state: active page (no router lib) and the global AI drawer. */

export type PageKey = "calendar" | "chores" | "focus";

type UiState = {
  page: PageKey;
  ai_drawer_open: boolean;
  set_page: (page: PageKey) => void;
  open_ai_drawer: () => void;
  close_ai_drawer: () => void;
};

export const use_ui_store = create<UiState>()((set) => ({
  page: "calendar",
  ai_drawer_open: false,
  set_page: (page) => set({ page }),
  open_ai_drawer: () => set({ ai_drawer_open: true }),
  close_ai_drawer: () => set({ ai_drawer_open: false }),
}));
