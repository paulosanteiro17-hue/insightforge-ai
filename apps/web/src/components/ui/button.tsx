import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant =
  "primary" | "secondary" | "ghost" | "outline" | "danger";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-ink-950 text-white shadow-sm hover:bg-ink-800 disabled:bg-ink-400",
  secondary:
    "bg-teal-500 text-white shadow-sm hover:bg-teal-600 disabled:bg-teal-400",
  ghost: "bg-transparent text-ink-600 hover:bg-ink-100 hover:text-ink-950",
  outline:
    "border border-ink-200 bg-white text-ink-800 shadow-sm hover:border-ink-300 hover:bg-ink-50",
  danger: "bg-coral-600 text-white hover:bg-coral-700"
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-9 rounded-lg px-3.5 text-sm",
  md: "h-11 rounded-xl px-4 text-sm",
  lg: "h-12 rounded-xl px-5 text-[0.9375rem]",
  icon: "size-11 rounded-xl"
};

export function buttonStyles({
  variant = "primary",
  size = "md",
  className
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}): string {
  return cn(
    "inline-flex shrink-0 items-center justify-center gap-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
    variantClasses[variant],
    sizeClasses[size],
    className
  );
}

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
    size?: ButtonSize;
  }
>(function Button(
  { className, variant = "primary", size = "md", type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonStyles({ variant, size, className })}
      {...props}
    />
  );
});
