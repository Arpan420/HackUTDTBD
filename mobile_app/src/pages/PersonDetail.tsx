// src/pages/PersonDetail.tsx
import { useParams, useNavigate } from "react-router-dom";
import { useMemo, useState } from "react";
import { usePeopleStore } from "../store/usePeopleStore";
import { DeletePersonButton } from "../components/people/DeletePersonButton";
import { EditPersonModal } from "../components/people/EditPersonModal";

export default function PersonDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const people = usePeopleStore((s) => s.people);
  const person = useMemo(() => people.find((p) => p.id === id), [people, id]);

  const [editOpen, setEditOpen] = useState(false);

  if (!person) {
    return (
      <div className="max-w-screen-sm mx-auto p-4">
        <button className="text-blue-600" onClick={() => navigate("/")}>← Back</button>
        <div className="mt-3 text-neutral-500">Person not found.</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-white/70 dark:bg-neutral-950/70 backdrop-blur border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-screen-sm mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <button className="text-blue-600" onClick={() => navigate("/")}>← Back</button>
          <div className="flex gap-2">
            <button
              className="px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700"
              onClick={() => setEditOpen(true)}
            >
              Edit Information
            </button>
            <DeletePersonButton
              personId={person.id}
              personName={person.Name}
              onDeleted={() => navigate("/")}
              className="px-3 py-2 rounded-lg bg-red-600 text-white"
            />
          </div>
        </div>
      </div>

      <main className="max-w-screen-sm mx-auto px-4 py-6 space-y-6">
        {/* Header block */}
        <section className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-full bg-neutral-200 dark:bg-neutral-800 flex items-center justify-center text-lg">
            {person.Name?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <h1 className="text-2xl font-semibold">{person.Name}</h1>
            {person.phoneNumber && (
              <div className="text-sm text-neutral-500">{person.phoneNumber}</div>
            )}
          </div>
        </section>

        {/* Details */}
        <section className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-xs uppercase text-neutral-500 mb-1">Phone</div>
            <div className="text-sm">
              {person.phoneNumber ?? <span className="text-neutral-400">—</span>}
            </div>
          </div>

          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-xs uppercase text-neutral-500 mb-1">Last seen</div>
            <div className="text-sm">
              {person.lastSeen
                ? new Date(person.lastSeen).toLocaleString()
                : <span className="text-neutral-400">—</span>}
            </div>
          </div>

          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 sm:col-span-2">
            <div className="text-xs uppercase text-neutral-500 mb-1">Notes</div>
            <div className="text-sm whitespace-pre-wrap break-words">
              {person.notes ?? <span className="text-neutral-400">—</span>}
            </div>
          </div>
        </section>

        {/* Summaries */}
        <section className="space-y-3">
          <h2 className="text-base font-medium">Summaries</h2>
          {person.summaries.length === 0 ? (
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 text-sm text-neutral-500">
              No summaries yet. Once generated, they’ll appear here.
            </div>
          ) : (
            <ul className="space-y-3">
              {person.summaries.map((s) => (
                <li key={s.id} className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
                  <div className="text-sm whitespace-pre-wrap break-words">{s.text}</div>
                  <div className="mt-2 text-xs text-neutral-500">
                    {new Date(s.createdAt).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>

      {/* Edit modal */}
      <EditPersonModal
        person={person}
        open={editOpen}
        onClose={() => setEditOpen(false)}
      />
    </div>
  );
}
