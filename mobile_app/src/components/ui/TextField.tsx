import type { FC, InputHTMLAttributes } from "react";
import clsx from "clsx";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
};

export const TextField: FC<Props> = ({ label, hint, className, ...rest }) => (
  <label className="block">
    <div className="text-xs text-neutral-500 mb-1">{label}</div>
    <input
      className={clsx(
        "w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm",
        className
      )}
      {...rest}
    />
    {hint && <div className="text-xs text-neutral-500 mt-1">{hint}</div>}
  </label>
);
