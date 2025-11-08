import type { FC } from "react";
import { Link } from "react-router-dom";
import type { Person } from "../types";
import dayjs from "../lib/dayjs";

export const PersonCard: FC<{ p: Person }> = ({ p }) => (
  <Link
    to={`/person/${p.id}`}
    className="block rounded-2xl border border-neutral-200 dark:border-neutral-800 p-3 hover:bg-neutral-50 dark:hover:bg-neutral-900"
  >
    <div className="flex flex-col gap-1">
      <div className="font-medium text-lg">{p.Name}</div>
      {p.lastSeen && (
        <div className="text-xs text-neutral-500">
          Last seen {dayjs(p.lastSeen).fromNow()}
        </div>
      )}
      {p.summaries[0] && (
        <div className="text-sm text-neutral-600 dark:text-neutral-300 mt-1 line-clamp-2">
          “{p.summaries[0].text}”
        </div>
      )}
      {p.phoneNumber && (
        <div className="text-xs text-neutral-500">Phone: {p.phoneNumber}</div>
      )}
    </div>
  </Link>
);
