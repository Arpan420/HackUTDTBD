import type {
  FC,
  PropsWithChildren,
  ButtonHTMLAttributes,
  InputHTMLAttributes
} from "react";
import clsx from "clsx";

type Props = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost" | "danger";
    block?: boolean;
    upload?: boolean;
    inputProps?: InputHTMLAttributes<HTMLInputElement>;
  }
>;

export const Button: FC<Props> = ({
  variant = "primary",
  block,
  className,
  upload,
  inputProps,
  children,
  ...rest
}) => {
  const base =
    "px-3 py-2 rounded-lg text-sm border transition " +
    "outline-none select-none " +
    "focus-visible:ring-2 focus-visible:ring-offset-1 " +
    "focus-visible:ring-blue-600 focus-visible:ring-offset-white " +
    "dark:focus-visible:ring-offset-neutral-900 " +
    "active:scale-[0.98]";

  const look = {
    primary:
      "bg-blue-600 text-white border-blue-600 " +
      "hover:bg-blue-700",
    secondary:
      "bg-white text-neutral-900 border-neutral-300 " +
      "hover:bg-neutral-50 " +
      "dark:bg-neutral-900 dark:text-neutral-50 " +
      "dark:border-neutral-700 dark:hover:bg-neutral-800",
    ghost:
      "bg-transparent text-neutral-700 border-transparent " +
      "hover:bg-neutral-100 " +
      "dark:text-neutral-300 dark:hover:bg-neutral-800",
    danger:
      "bg-red-600 text-white border-red-600 " +
      "hover:bg-red-700"
  }[variant];

  if (upload) {
    return (
      <label className={clsx("relative inline-flex", block && "w-full")}>
        <span className={clsx(base, look, className)}>{children}</span>
        <input
          type="file"
          className="absolute inset-0 opacity-0 cursor-pointer"
          {...inputProps}
        />
      </label>
    );
  }

  return (
    <button
      className={clsx(base, look, block && "w-full", className)}
      {...rest}
    >
      {children}
    </button>
  );
};
