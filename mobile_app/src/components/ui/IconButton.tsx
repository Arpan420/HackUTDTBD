import type { FC, ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement>;

export const IconButton: FC<Props> = ({ className, ...rest }) => {
  return (
    <button
      className={clsx(
        "p-2 rounded-lg outline-none transition select-none " +
          "hover:bg-neutral-100 active:scale-[0.98] " +
          "focus-visible:ring-2 focus-visible:ring-offset-1 " +
          "focus-visible:ring-blue-600 focus-visible:ring-offset-white " +
          "dark:hover:bg-neutral-800 dark:focus-visible:ring-offset-neutral-900",
        className
      )}
      {...rest}
    />
  );
};
