import type { FC } from "react";
import { useState } from "react";
import { TextField } from "../ui/TextField";
import { Button } from "../ui/Button";
import { usePeopleStore } from "../../store/usePeopleStore";

export const AddPersonBar: FC = () => {
  const addPerson = usePeopleStore((s) => s.addPerson);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  const onAdd = () => {
    if (!name.trim()) return;
    addPerson({ Name: name.trim(), phoneNumber: phone.trim() || undefined });
    setName("");
    setPhone("");
  };

  return (
    <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 p-3 space-y-2">
      <div className="font-medium text-sm">Add Person</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <div className="flex items-end">
          <Button onClick={onAdd} className="w-full">Add</Button>
        </div>
      </div>
    </div>
  );
};
