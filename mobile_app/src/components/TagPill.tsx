import type { FC } from "react";

export const TagPill: FC<{ text: string }> = ({ text }) => (
  <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300">
    {text}
  </span>
);
