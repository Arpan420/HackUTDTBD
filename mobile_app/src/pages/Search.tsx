import { useMemo, useState } from "react";
import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";
import { usePeopleStore } from "../store/usePeopleStore";
import { PersonCard } from "../components/PersonCard";

export default function Search() {
  const [q, setQ] = useState("");
  const people = usePeopleStore((s) => s.people);

  const results = useMemo(() => {
    const k = q.trim().toLowerCase();
    if (!k) return [];
    return people.filter((p) => {
      const inName = p.Name.toLowerCase().includes(k);
      const inPhone = (p.phoneNumber ?? "").toLowerCase().includes(k);
      const inSums = p.summaries.some((s) => s.text.toLowerCase().includes(k));
      const inNotes = p.interactions.some(
        (i) =>
          (i.notes ?? "").toLowerCase().includes(k) ||
          (i.location ?? "").toLowerCase().includes(k)
      );
      return inName || inPhone || inSums || inNotes;
    });
  }, [q, people]);

  return (
    <div className="pb-20">
      <TopBar title="Search" />
      <main className="max-w-screen-sm mx-auto p-4 space-y-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search names, phone, summaries, notes, locations…"
          className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2"
        />
        {q === "" ? (
          <div className="text-sm text-neutral-500">
            Type to search across names, phone numbers, AI summaries, and interaction notes.
          </div>
        ) : results.length === 0 ? (
          <div className="text-sm text-neutral-500">No results.</div>
        ) : (
          results.map((p) => <PersonCard key={p.id} p={p} />)
        )}
      </main>
      <BottomNav />
    </div>
  );
}
