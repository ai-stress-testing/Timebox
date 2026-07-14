import { use_toast_store } from "../../Store/toast-store";
import type { Toast, ToastTone } from "../../Store/toast-store";

/* tone -> accent classes (dispatch map) */
const tone_classes: Record<ToastTone, string> = {
  ok: "border-ok/50 text-ok",
  danger: "border-danger/50 text-danger",
  info: "border-accent/50 text-hi",
};

function ToastCard({ toast }: { toast: Toast }) {
  const dismiss = use_toast_store((state) => state.dismiss);
  return (
    <div
      role="status"
      className={`animate-pop-in flex items-center gap-3 rounded-lg border
        bg-surface-2 px-4 py-3 text-sm shadow-raised
        ${tone_classes[toast.tone]}`}
    >
      <span className="text-hi">{toast.message}</span>
      <button
        aria-label="Dismiss notification"
        className="cursor-pointer text-low transition-colors
          duration-(--tb-dur-fast) hover:text-hi"
        onClick={() => dismiss(toast.id)}
      >
        <span aria-hidden="true">✕</span>
      </button>
    </div>
  );
}

export function ToastViewport() {
  const toasts = use_toast_store((state) => state.toasts);
  return (
    <div
      aria-live="polite"
      className="fixed right-4 bottom-4 z-100 flex flex-col gap-2"
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
