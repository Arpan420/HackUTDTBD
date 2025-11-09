import type { FC } from "react";
import { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import { TextField } from "../ui/TextField";
import { Button } from "../ui/Button";
import { usePeopleStore } from "../../store/usePeopleStore";
import type { Person } from "../../types";

type Props = {
  person: Person;
  open: boolean;
  onClose: () => void;
};

export const EditPersonModal: FC<Props> = ({
  person,
  open,
  onClose
}) => {
  const updatePerson = usePeopleStore((s) => s.updatePerson);
  const addSummary = usePeopleStore((s) => s.addSummary);
  const addInteraction = usePeopleStore((s) => s.addInteraction);

  const [name, setName] = useState(person.Name);
  const [phone, setPhone] = useState(person.phoneNumber ?? "");
  const [notes, setNotes] = useState(person.notes ?? "");
  const [lastSeen, setLastSeen] = useState(person.lastSeen ?? "");

  // optional new items
  const [newSummary, setNewSummary] = useState("");
  const [iWhen, setIWhen] = useState("");
  const [iLocation, setILocation] = useState("");
  const [iNotes, setINotes] = useState("");

  useEffect(() => {
    if (open) {
      setName(person.Name);
      setPhone(person.phoneNumber ?? "");
      setNotes(person.notes ?? "");
      setLastSeen(person.lastSeen ?? "");
      setNewSummary("");
      setIWhen("");
      setILocation("");
      setINotes("");
    }
  }, [open, person]);

  const onSave = () => {
    updatePerson(person.id, {
      Name: name.trim(),
      phoneNumber: phone.trim() || undefined,
      notes: notes.trim() || undefined,
      lastSeen: lastSeen || undefined,
    });

    if (newSummary.trim()) {
      addSummary(person.id, { text: newSummary.trim() });
    }

    if (iWhen) {
      addInteraction(person.id, {
        when: iWhen,
        location: iLocation || undefined,
        notes: iNotes || undefined,
      });
    }

    onClose();
  };

  return (
    <Modal title="Edit Person" open={open} onClose={onClose}>
      <div className="space-y-3">
        <TextField label="Name" value={name}
                   onChange={(e) => setName(e.target.value)} />

        <TextField label="Phone" value={phone}
                   onChange={(e) => setPhone(e.target.value)}
                   placeholder="555-123-9876" />

        <TextField label="Last seen (ISO)" value={lastSeen}
                   onChange={(e) => setLastSeen(e.target.value)}
                   placeholder="2025-11-07T21:00:00Z" />

        <TextField label="Notes" value={notes}
                   onChange={(e) => setNotes(e.target.value)}
                   placeholder="Additional context about this person" />

        <div className="pt-2">
          <div className="text-xs font-semibold mb-2">
            Quick add (optional)
          </div>

          <TextField label="New summary" value={newSummary}
                     onChange={(e) => setNewSummary(e.target.value)}
                     placeholder="Short AI-like note to add" />

          <div className="grid grid-cols-1 gap-2">
            <TextField label="Interaction when (ISO)" value={iWhen}
                       onChange={(e) => setIWhen(e.target.value)}
                       placeholder="2025-11-07T21:00:00Z" />
            <TextField label="Location" value={iLocation}
                       onChange={(e) => setILocation(e.target.value)}
                       placeholder="e.g., Library" />
            <TextField label="Interaction notes" value={iNotes}
                       onChange={(e) => setINotes(e.target.value)} />
          </div>
        </div>

        <div className="flex gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onSave}>Save</Button>
        </div>
      </div>
    </Modal>
  );
};
