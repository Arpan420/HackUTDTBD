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

export const EditPersonModal: FC<Props> = ({ person, open, onClose }) => {
  const updatePerson = usePeopleStore((s) => s.updatePerson);
  const addSummary = usePeopleStore((s) => s.addSummary);
  const addInteraction = usePeopleStore((s) => s.addInteraction);

  // Base profile fields (Name is read-only to avoid breaking person_id/FK)
  const [phone, setPhone] = useState(person.phoneNumber ?? "");
  const [notes, setNotes] = useState(person.notes ?? "");
  const [lastSeen, setLastSeen] = useState(person.lastSeen ?? "");

  // Quick add
  const [newSummary, setNewSummary] = useState("");
  // Store a local datetime string for the input, convert to ISO on save
  const [iWhenLocal, setIWhenLocal] = useState("");
  const [iLocation, setILocation] = useState("");
  const [iNotes, setINotes] = useState("");

  useEffect(() => {
    if (!open) return;
    setPhone(person.phoneNumber ?? "");
    setNotes(person.notes ?? "");
    setLastSeen(person.lastSeen ?? "");

    setNewSummary("");
    setIWhenLocal("");
    setILocation("");
    setINotes("");
  }, [open, person]);

  const onSave = () => {
    // Update base profile fields
    updatePerson(person.id, {
      // Name intentionally omitted (stable route/ID)
      phoneNumber: phone.trim() || undefined,
      notes: notes.trim() || undefined,
      lastSeen: lastSeen || undefined,
    });

    // Optional quick add summary
    if (newSummary.trim()) {
      addSummary(person.id, { text: newSummary.trim() });
      // If you later want to link the new interaction to this summary,
      // return the id from addSummary and pass it below as summaryId.
    }

    // Optional quick add interaction
    if (iWhenLocal) {
      // Convert 'YYYY-MM-DDTHH:mm' to ISO
      const iso = new Date(iWhenLocal).toISOString();
      addInteraction(person.id, {
        when: iso,
        location: iLocation || undefined,
        notes: iNotes || undefined,
        // summaryId: (optional) if you want to link to the newly created summary
      });
    }

    onClose();
  };

  return (
    <Modal title="Edit Information" open={open} onClose={onClose}>
      <div className="space-y-3">
        {/* Read-only: Name is your stable person_id */}
        <TextField label="Name (ID)" value={person.Name} disabled />

        <TextField
          label="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="(555) 123-9876"
        />

        <TextField
          label="Notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Additional context about this person…"
        />

        <TextField
          label="Last seen (ISO)"
          value={lastSeen}
          onChange={(e) => setLastSeen(e.target.value)}
          placeholder="2025-11-07T21:00:00Z"
        />

        <div className="pt-2">
          <div className="text-xs font-semibold mb-2">Quick add (optional)</div>

          <TextField
            label="New summary"
            value={newSummary}
            onChange={(e) => setNewSummary(e.target.value)}
            placeholder="Short note to add"
          />

          <div className="grid grid-cols-1 gap-2">
            <TextField
              label="Interaction date/time"
              type="datetime-local"
              value={iWhenLocal}
              onChange={(e) => setIWhenLocal(e.target.value)}
            />
            <TextField
              label="Interaction location"
              value={iLocation}
              onChange={(e) => setILocation(e.target.value)}
              placeholder="e.g., Library"
            />
            <TextField
              label="Interaction notes"
              value={iNotes}
              onChange={(e) => setINotes(e.target.value)}
              placeholder="Add any quick notes"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-1 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={onSave}>Save</Button>
        </div>
      </div>
    </Modal>
  );
};
