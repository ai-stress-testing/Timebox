import type { ComponentPropsWithoutRef } from "react";

export type ButtonVariant = "primary" | "ghost" | "danger" | "subtle";

const base_classes =
  "inline-flex cursor-pointer items-center justify-center gap-2 rounded-full " +
  "px-4 py-2 text-sm font-medium transition-all duration-(--tb-dur-fast) " +
  "ease-spring hover:-translate-y-px active:scale-95 active:translate-y-0 " +
  "disabled:pointer-events-none disabled:opacity-50";

/* variant -> token-driven classes (dispatch map, no conditionals) */
const variant_classes: Record<ButtonVariant, string> = {
  primary:
    "[background:var(--tb-gradient-accent)] text-accent-ink shadow-glow " +
    "hover:brightness-110",
  ghost:
    "border border-edge bg-surface-2 text-hi hover:border-edge-strong " +
    "hover:bg-surface-3",
  danger:
    "border border-danger/40 bg-danger/10 text-danger hover:bg-danger/20",
  subtle: "text-mid hover:bg-surface-2 hover:text-hi",
};

type ButtonProps = ComponentPropsWithoutRef<"button"> & {
  variant?: ButtonVariant;
};

export function Button({
  variant = "ghost",
  className = "",
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${base_classes} ${variant_classes[variant]} ${className}`}
      {...rest}
    />
  );
}
