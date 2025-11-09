import type { FC } from "react";
import { Modal } from "./Modal";

type Props = {
  open: boolean;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export const Confirm: FC<Props> = ({
  open,
  title = "Confirm",
  message = "Are you sure?",
  confirmText = "Delete",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
}) => (
  <Modal title={title} open={open} onClose={onCancel}>
    <p className="text-sm text-neutral-600 dark:text-neutral-300">{message}</p>
    <div className="flex gap-2 justify-end pt-3">
      <button className="px-3 py-2 rounded-lg border dark:border-neutral-800" onClick={onCancel}>
        {cancelText}
      </button>
      <button className="px-3 py-2 rounded-lg bg-red-600 text-white" onClick={onConfirm}>
        {confirmText}
      </button>
    </div>
  </Modal>
);
