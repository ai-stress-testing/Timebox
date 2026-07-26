import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";

type SliderProps = {
  label: string;
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  onCommit: (value: number) => void;
};

/**
 * Labeled range slider matching `FieldShell`'s label style. Fires `onChange`
 * continuously while dragging (for a live readout) and `onCommit` only on
 * release — mirrors the backend contract of "PATCH on release, not
 * continuously."
 */
export function Slider({ label, min, max, value, onChange, onCommit }: SliderProps) {
  const [draft, set_draft] = useState(value);

  useEffect(() => {
    set_draft(value);
  }, [value]);

  const handle_input = (event: ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    set_draft(next);
    onChange(next);
  };

  const commit = () => onCommit(draft);

  return (
    <label className="block">
      <span className="mb-1 flex items-center justify-between text-xs font-medium
        tracking-wide text-mid uppercase">
        <span>{label}</span>
        <span className="text-hi normal-case">every {draft} days</span>
      </span>
      <input
        type="range"
        className="w-full cursor-pointer accent-accent"
        min={min}
        max={max}
        step={1}
        value={draft}
        onChange={handle_input}
        onPointerUp={commit}
        onKeyUp={commit}
      />
    </label>
  );
}
