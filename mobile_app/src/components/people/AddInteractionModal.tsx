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

export const AddInteractionModal: FC<Props> = ({
  personId,
  open,
  onClose,
  defaultSummaryId,
}) => {
  const addInteraction = usePeopleStore((s) => s.addInteraction);

  const [location, setLocation] = useState("");
  const [notes, setNotes] = useState("");
  const [summaryId, setSummaryId] = useState(defaultSummaryId ?? "");

  // Store the datetime-local string (YYYY-MM-DDTHH:mm)
  const [when, setWhen] = useState<string>(() =>
    new Date().toISOString().slice(0, 16)
  );

  useEffect(() => {
    if (open) {
      setLocation("");
      setNotes("");
      setSummaryId(defaultSummaryId ?? "");
      setWhen(new Date().toISOString().slice(0, 16));
    }
  }, [open, defaultSummaryId]);

  const onSave = () => {
    if (!summaryId.trim()) return; // if you want summaryId required in UI

    // Convert datetime-local string -> ISO string
    const iso = (() => {
      try {
        const d = new Date(when);
        return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
      } catch {
        return new Date().toISOString();
      }
    })();

    addInteraction(personId, {
      when: iso,                                 // <-- string as required
      location: location || undefined,
      notes: notes || undefined,
      summaryId: summaryId || undefined,
    });

    onClose();
  };

  return (
    <Modal title="Add Interaction" open={open} onClose={onClose}>
      <TextField
        label="Summary ID (required)"
        value={summaryId}
        onChange={(e) => setSummaryId(e.target.value)}
        hint="Link the interaction to an existing summary ID."
      />

      {/* If your TextField supports type, keep this; otherwise swap to a native <input> */}
      <TextField
        type="datetime-local"
        label="When"
        value={when}
        onChange={(e) => setWhen(e.target.value)}
      />

      <TextField
        label="Location"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
      />
      <TextField
        label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={onSave}>Add</Button>
      </div>
    </Modal>
  );
};
