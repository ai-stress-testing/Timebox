import { weekday_options } from "../../lib/dispatch-maps/labels";

type WeekdayTogglesProps = {
  label: string;
  selected: number[];
  on_toggle: (value: number) => void;
};

/** Weekday chip toggles (Sun=0..Sat=6) — shared shape with chores' DayToggles. */
export function WeekdayToggles({ label, selected, on_toggle }: WeekdayTogglesProps) {
  return (
    <fieldset>
      <legend className="mb-1 block text-xs font-medium tracking-wide text-mid uppercase">
        {label}
      </legend>
      <div className="flex flex-wrap gap-1">
        {weekday_options.map((option) => {
          const active = selected.includes(option.value);
          const classes = active
            ? "[background:var(--tb-gradient-accent)] text-accent-ink"
            : "border border-edge text-mid hover:text-hi";
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => on_toggle(option.value)}
              className={`cursor-pointer rounded-full px-3 py-1 text-xs
                font-medium transition-all duration-(--tb-dur-fast)
                ease-spring ${classes}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
