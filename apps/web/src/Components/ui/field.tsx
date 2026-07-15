import type { ComponentPropsWithoutRef, ReactNode } from "react";

export const input_classes =
  "w-full rounded-md border border-edge bg-surface-2 px-3 py-2 text-sm " +
  "text-hi placeholder:text-low transition-colors duration-(--tb-dur-fast) " +
  "hover:border-edge-strong";

type ShellProps = { label: string; error?: string; children: ReactNode };

function FieldShell({ label, error, children }: ShellProps) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium tracking-wide text-mid uppercase">
        {label}
      </span>
      {children}
      {error ? <span className="mt-1 block text-xs text-danger">{error}</span> : null}
    </label>
  );
}

type InputProps = ComponentPropsWithoutRef<"input"> & {
  label: string;
  error?: string;
};

export function TextField({ label, error, ...rest }: InputProps) {
  return (
    <FieldShell label={label} error={error}>
      <input className={input_classes} {...rest} />
    </FieldShell>
  );
}

type SelectProps = ComponentPropsWithoutRef<"select"> & {
  label: string;
  error?: string;
};

export function SelectField({ label, error, children, ...rest }: SelectProps) {
  return (
    <FieldShell label={label} error={error}>
      <select className={input_classes} {...rest}>
        {children}
      </select>
    </FieldShell>
  );
}

type TextAreaProps = ComponentPropsWithoutRef<"textarea"> & {
  label: string;
  error?: string;
};

export function TextAreaField({ label, error, ...rest }: TextAreaProps) {
  return (
    <FieldShell label={label} error={error}>
      <textarea className={`${input_classes} min-h-20 resize-y`} {...rest} />
    </FieldShell>
  );
}

type CheckboxProps = ComponentPropsWithoutRef<"input"> & { label: string };

export function CheckboxField({ label, ...rest }: CheckboxProps) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-hi">
      <input type="checkbox" className="size-4 accent-accent" {...rest} />
      {label}
    </label>
  );
}
