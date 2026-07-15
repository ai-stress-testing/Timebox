import { create } from "zustand";

export type ToastTone = "ok" | "danger" | "info";
export type Toast = { id: number; message: string; tone: ToastTone };

type ToastState = {
  toasts: Toast[];
  push: (message: string, tone: ToastTone) => void;
  dismiss: (id: number) => void;
};

const toast_lifetime_ms = 4600;
let next_toast_id = 1;

export const use_toast_store = create<ToastState>()((set) => ({
  toasts: [],
  push: (message, tone) => {
    const id = next_toast_id;
    next_toast_id += 1;
    set((state) => ({ toasts: [...state.toasts, { id, message, tone }] }));
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((toast) => toast.id !== id),
      }));
    }, toast_lifetime_ms);
  },
  dismiss: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));

export function push_toast(message: string, tone: ToastTone = "info"): void {
  use_toast_store.getState().push(message, tone);
}
