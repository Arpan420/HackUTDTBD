import type { FC } from "react";
import { Link, useLocation } from "react-router-dom";
import { Settings, Plus, Home } from "lucide-react";
import { IconButton } from "./ui/IconButton";

type Props = {
  title: string;
  onAddPerson?: () => void;
};

export const TopBar: FC<Props> = ({ title, onAddPerson }) => {
  const location = useLocation();
  const isSettingsPage = location.pathname === "/settings";

  return (
    <div
      className="sticky top-0 z-10 bg-white/90 dark:bg-neutral-900/90
                 backdrop-blur border-b border-neutral-200
                 dark:border-neutral-800"
    >
      <div
        className="max-w-screen-sm mx-auto px-4 h-12 flex items-center
                   justify-between gap-2"
      >
        <span className="font-semibold text-lg truncate">{title}</span>

        <div className="flex items-center gap-1">
          {onAddPerson && (
            <IconButton
              aria-label="Add person"
              onClick={onAddPerson}
              title="Add person"
            >
              <Plus className="w-5 h-5" />
            </IconButton>
          )}

          {isSettingsPage ? (
            <Link to="/" aria-label="Home" title="Home">
              <IconButton>
                <Home className="w-5 h-5" />
              </IconButton>
            </Link>
          ) : (
            <Link to="/settings" aria-label="Settings" title="Settings">
              <IconButton>
                <Settings className="w-5 h-5" />
              </IconButton>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};
