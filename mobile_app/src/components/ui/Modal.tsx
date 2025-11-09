import type { FC, PropsWithChildren } from "react";
import { X } from "lucide-react";

type Props = PropsWithChildren<{
  title: string;
  open: boolean;
  onClose: () => void;
}>;

export const Modal: FC<Props> = ({ title, open, onClose, children }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full sm:max-w-md bg-white dark:bg-neutral-900 rounded-t-2xl sm:rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold">{title}</h3>
          <button className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg" onClick={onClose}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">{children}</div>
      </div>
    </div>
  );
};
