import { useRef, useState } from "react";
import type { DragEvent } from "react";

type KeyDropZoneProps = {
  disabled?: boolean;
  on_file: (file: File) => void;
};

/** Drag-and-drop / file-picker zone for the timebox.key file. */
export function KeyDropZone({ disabled = false, on_file }: KeyDropZoneProps) {
  const input_ref = useRef<HTMLInputElement | null>(null);
  const [drag_active, set_drag_active] = useState(false);

  const handle_drop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    set_drag_active(false);
    const file = event.dataTransfer.files.item(0);
    if (file) on_file(file);
  };

  const zone_classes = drag_active
    ? "border-accent bg-surface-2 shadow-glow-soft"
    : "border-edge bg-surface-1 hover:border-edge-strong hover:bg-surface-2";

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        aria-label="Choose or drop your Timebox key file"
        onClick={() => input_ref.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          set_drag_active(true);
        }}
        onDragLeave={() => set_drag_active(false)}
        onDrop={handle_drop}
        className={`block w-full cursor-pointer rounded-lg border-2
          border-dashed p-8 text-center transition-all
          duration-(--tb-dur-base) ease-spring ${zone_classes}`}
      >
        <span className="font-display block text-lg font-semibold text-hi">
          Drop your <span className="text-accent-2">timebox.key</span> here
        </span>
        <span className="mt-1 block text-sm text-mid">
          …or click to browse for it
        </span>
      </button>
      <input
        ref={input_ref}
        type="file"
        accept=".key,.json,application/json"
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(event) => {
          const file = event.target.files?.item(0);
          if (file) on_file(file);
          event.target.value = "";
        }}
      />
    </>
  );
}
