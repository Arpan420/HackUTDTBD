import type { FC } from "react";
import { Link } from "react-router-dom";
import { Settings } from "lucide-react";

export const TopBar: FC<{ title: string }> = ({ title }) => (
  <div className="sticky top-0 z-10 bg-white/90 dark:bg-neutral-900/90 backdrop-blur border-b border-neutral-200 dark:border-neutral-800">
    <div className="max-w-screen-sm mx-auto px-4 h-12 flex items-center justify-between">
      <span className="font-semibold text-lg truncate">{title}</span>
      <Link
        to="/settings"
        className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800"
      >
        <Settings className="w-5 h-5" />
      </Link>
    </div>
  </div>
);
