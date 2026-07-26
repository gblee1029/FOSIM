import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  const styles = {
    primary: "bg-graphite text-white hover:bg-black",
    secondary: "border border-slate-300 bg-white text-graphite hover:bg-slate-50",
    ghost: "text-graphite hover:bg-slate-100",
  };
  return (
    <button
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}
