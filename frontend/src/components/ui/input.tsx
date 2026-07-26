import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-graphite outline-none transition focus:border-graphite focus:ring-2 focus:ring-slate-200",
        className,
      )}
      {...props}
    />
  );
}
