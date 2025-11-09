import { useState } from "react";
import { usePeopleStore } from "../../store/usePeopleStore";
import { Confirm } from "../ui/Confirm";

type Props = {
  personId: string;         // internal Person.id in your store
  personName: string;       // display name (faces.person_id)
  className?: string;
  onDeleted?: () => void;   // e.g., navigate("/")
};

export function DeletePersonButton({ personId, personName, className, onDeleted }: Props) {
  const deletePerson = usePeopleStore((s) => s.deletePerson);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleDelete = async () => {
    try {
      setBusy(true);
      await deletePerson(personId);
      setOpen(false);
      onDeleted?.();
    } catch (e) {
      console.error(e);
      alert("Failed to delete this person. Check console for details.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        disabled={busy}
        className={className ?? "px-3 py-2 rounded-lg bg-red-600 text-white disabled:opacity-50"}
      >
        {busy ? "Deleting..." : "Delete Person"}
      </button>

      <Confirm
        open={open}
        title="Delete person"
        message={`This will permanently remove "${personName}" and all of their summaries.`}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleDelete}
        onCancel={() => setOpen(false)}
      />
    </>
  );
}
