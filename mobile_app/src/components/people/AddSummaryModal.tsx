import type { FC } from "react";
import { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import { TextField } from "../ui/TextField";
import { Button } from "../ui/Button";
import { usePeopleStore } from "../../store/usePeopleStore";

type Props = {
  personId: string;
  open: boolean;
  onClose: () => void;
};

export const AddSummaryModal: FC<Props> = ({ personId, open, onClose }) => {
  const addSummary = usePeopleStore((s) => s.addSummary);
  const [text, setText] = useState("");
  useEffect(() => {
    if (open) setText("");
  }, [open]);

  const onSave = () => {
    if (!text.trim()) return;
    addSummary(personId, { text: text.trim(), sources: [] });
    onClose();
  };

  return (
    <Modal title="Add AI Summary" open={open} onClose={onClose}>
      <TextField label="Summary Text" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={onSave}>Add</Button>
      </div>
    </Modal>
  );
};
