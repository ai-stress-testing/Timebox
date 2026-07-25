import type { CalendarColor } from "../../lib/api-schemas";
import { calendar_color_var } from "../../lib/dispatch-maps/event-colors";
import { calendar_color_options } from "../../lib/dispatch-maps/labels";

type ColorSwatchPickerProps = {
  value: CalendarColor;
  on_change: (color: CalendarColor) => void;
};

/** Radio-group of calendar_color swatches — the only color picker in the app,
 * shared by the event form's inline type creator and the Settings type manager. */
export function ColorSwatchPicker({ value, on_change }: ColorSwatchPickerProps) {
  return (
    <div role="radiogroup" aria-label="Color" className="flex flex-wrap gap-2">
      {calendar_color_options.map((color) => (
        <button
          key={color}
          type="button"
          role="radio"
          aria-checked={value === color}
          aria-label={color}
          onClick={() => on_change(color)}
          className={`size-6 cursor-pointer rounded-full border-2 transition-transform
            duration-(--tb-dur-fast) ease-spring hover:scale-110
            ${value === color ? "border-hi scale-110" : "border-transparent"}`}
          style={{ background: calendar_color_var[color] }}
        />
      ))}
    </div>
  );
}
