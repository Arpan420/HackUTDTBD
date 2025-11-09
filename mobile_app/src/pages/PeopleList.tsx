import { useState } from "react";
import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";
import { usePeopleStore } from "../store/usePeopleStore";
import { PersonCard } from "../components/PersonCard";
import { AddPersonModal } from "../components/people/AddPersonModal.tsx";

export default function PeopleList() {
  const people = usePeopleStore((s) => s.people);
  const [open, setOpen] = useState(false);

  return (
    <div className="pb-20">
      <TopBar title="People" onAddPerson={() => setOpen(true)} />

      <main className="max-w-screen-sm mx-auto p-4 space-y-3">
        {people.length === 0 && (
          <div className="text-sm text-neutral-500">
            No people yet. After the AI summarizes a conversation, a
            profile will appear here.
          </div>
        )}
        {people.map((p) => (
          <PersonCard key={p.id} p={p} />
        ))}
      </main>

      <BottomNav />

      <AddPersonModal open={open} onClose={() => setOpen(false)} />
    </div>
  );
}
