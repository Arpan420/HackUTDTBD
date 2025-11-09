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
  defaultSummaryId?: string;
};

export const AddInteractionModal: FC<Props> = ({ personId, open, onClose, defaultSummaryId }) => {
  const addInteraction = usePeopleStore((s) => s.addInteraction);
  const [location, setLocation] = useState("");
  const [notes, setNotes] = useState("");
  const [summaryId, setSummaryId] = useState(defaultSummaryId ?? "");

  useEffect(() => {
    if (open) {
      setLocation("");
      setNotes("");
      setSummaryId(defaultSummaryId ?? "");
    }
  }, [open, defaultSummaryId]);

  const onSave = () => {
    if (!summaryId.trim()) return; // required by your type
    addInteraction(personId, { location: location || undefined, notes: notes || undefined, summaryId });
    onClose();
  };

  return (
    <Modal title="Add Interaction" open={open} onClose={onClose}>
      <TextField label="Summary ID (required)" value={summaryId} onChange={(e) => setSummaryId(e.target.value)} hint="Link the interaction to an existing summary ID." />
      <TextField label="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
      <TextField label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={onSave}>Add</Button>
      </div>
    </Modal>
  );
};
