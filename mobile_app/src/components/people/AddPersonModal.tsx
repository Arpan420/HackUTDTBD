import type { FC } from "react";
import { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import { TextField } from "../ui/TextField";
import { Button } from "../ui/Button";
import { usePeopleStore } from "../../store/usePeopleStore";

type Props = {
  open: boolean;
  onClose: () => void;
};

export const AddPersonModal: FC<Props> = ({ open, onClose }) => {
  const addPerson = usePeopleStore((s) => s.addPerson);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  useEffect(() => {
    if (open) {
      setName("");
      setPhone("");
    }
  }, [open]);

  const onSave = () => {
    if (!name.trim()) return;
    addPerson({ Name: name.trim(), phoneNumber: phone.trim() || undefined });
    onClose();
  };

  return (
    <Modal title="Add Person" open={open} onClose={onClose}>
      <TextField
        label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <TextField
        label="Phone (optional)"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
      />
      <div className="flex gap-2 pt-1">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={onSave}>Save</Button>
      </div>
    </Modal>
  );
};
