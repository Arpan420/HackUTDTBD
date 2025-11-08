import type { FC } from "react";
import dayjs from "dayjs";
import type { Summary } from "../types";

export const SummaryCard: FC<{ s: Summary }> = ({ s }) => (
  <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-3">
    <div className="text-xs text-neutral-500 mb-1">
      {dayjs(s.createdAt).format("MMM D, HH:mm")}
    </div>
    <div className="text-sm">{s.text}</div>
  </div>
);
