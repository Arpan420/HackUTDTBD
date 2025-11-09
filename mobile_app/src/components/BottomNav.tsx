import type { FC } from "react";
import { Home, Search, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

type NavItemProps = {
  to: string;
  icon: LucideIcon;
  label: string;
};

const Item: FC<NavItemProps> = ({
  to,
  icon: Icon,
  label
}) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      [
        "flex flex-col items-center justify-center flex-1 py-2",
        "transition select-none outline-none",
        "hover:bg-neutral-50 active:opacity-80",
        "focus-visible:ring-2 focus-visible:ring-offset-1",
        "focus-visible:ring-blue-600 focus-visible:ring-offset-white",
        "dark:hover:bg-neutral-900",
        "dark:focus-visible:ring-offset-neutral-900",
        isActive ? "text-blue-600" : "text-neutral-500"
      ].join(" ")
    }
  >
    <Icon className="w-5 h-5" />
    <span className="text-xs mt-1">{label}</span>
  </NavLink>
);

export const BottomNav: FC = () => (
  <nav
    className="fixed bottom-0 left-0 right-0 bg-white dark:bg-neutral-900
               border-t border-neutral-200 dark:border-neutral-800"
  >
    <div className="max-w-screen-sm mx-auto flex">
      <Item to="/" icon={Home} label="People" />
      <Item to="/search" icon={Search} label="Search" />
      <Item to="/settings" icon={User} label="Me" />
    </div>
  </nav>
);
