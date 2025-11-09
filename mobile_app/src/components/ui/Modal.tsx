// src/components/ui/Modal.tsx
import type { FC, PropsWithChildren, MouseEvent } from "react";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

type Props = PropsWithChildren<{
  title: string;
  open: boolean;
  onClose: () => void;
}>;

export const Modal: FC<Props> = ({ title, open, onClose, children }) => {
  // ✅ Hooks always run
  useEffect(() => {
    if (!open) return;

    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // ✅ Return early AFTER hooks
  if (!open) return null;

  const stop = (e: MouseEvent) => {
    e.stopPropagation();
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[10000] flex items-end sm:items-center justify-center"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
    >
      <div className="fixed inset-0 bg-black/50" />

      <div
        className="relative z-[10001] w-full sm:max-w-md bg-white dark:bg-neutral-900 rounded-t-2xl sm:rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4 mx-2"
        onClick={stop}
      >
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold">{title}</h3>
          <button
            type="button"
            className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">{children}</div>
      </div>
    </div>,
    document.body
  );
};
