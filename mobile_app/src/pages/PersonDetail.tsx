import { useParams } from "react-router-dom";
import { useState } from "react";
import dayjs from "../lib/dayjs";
import { usePeopleStore } from "../store/usePeopleStore";
import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";
import { Button } from "../components/ui/Button";
import { EditPersonModal } from "../components/people/EditPersonModal";

export default function PersonDetail() {
  const { id } = useParams();
  const person = usePeopleStore(
    (s) => s.people.find((p) => p.id === id)
  );

  const [open, setOpen] = useState(false);

  if (!person) {
    return (
      <div className="pb-20">
        <TopBar title="Person" />
        <main className="max-w-screen-sm mx-auto p-4">
          <div className="text-sm text-neutral-500">
            Person not found.
          </div>
        </main>
        <BottomNav />
      </div>
    );
  }

  return (
    <div className="pb-20">
      <TopBar title={person.Name} />

      <main className="max-w-screen-sm mx-auto p-4 space-y-4">
        {/* Header card */}
        <div
          className="flex items-start justify-between gap-3 p-3
                     rounded-2xl border border-neutral-200
                     dark:border-neutral-800"
        >
          <div className="text-sm">
            {person.phoneNumber && (
              <div>
                <span className="text-neutral-500">Phone:</span>{" "}
                {person.phoneNumber}
              </div>
            )}

            {person.lastSeen && (
              <div>
                <span className="text-neutral-500">Last seen:</span>{" "}
                {dayjs(person.lastSeen).format("MMM D, YYYY")}
              </div>
            )}

            {person.notes && (
              <div className="mt-2 text-neutral-400 line-clamp-2">
                {person.notes}
              </div>
            )}
          </div>

          <Button onClick={() => setOpen(true)}>Edit</Button>
        </div>

        {/* Summaries */}
        <section className="space-y-2">
          <h3 className="font-semibold">AI Summaries</h3>
          {person.summaries.length === 0 ? (
            <div className="text-sm text-neutral-500">
              No summaries yet.
            </div>
          ) : (
            person.summaries.map((s) => (
              <div
                key={s.id}
                className="rounded-2xl border p-3
                           border-neutral-200 dark:border-neutral-800"
              >
                <div className="text-xs text-neutral-500 mb-1">
                  {dayjs(s.createdAt).format("MMM D, HH:mm")}
                </div>
                <div>{s.text}</div>
              </div>
            ))
          )}
        </section>

        {/* Interactions */}
        <section className="space-y-2">
          <h3 className="font-semibold">Recent Interactions</h3>
          {person.interactions.length === 0 ? (
            <div className="text-sm text-neutral-500">
              No interactions yet.
            </div>
          ) : (
            person.interactions.map((i) => (
              <div
                key={i.id}
                className="rounded-2xl border p-3
                           border-neutral-200 dark:border-neutral-800"
              >
                <div className="text-xs text-neutral-500 mb-1">
                  {dayjs(i.when).format("MMM D, HH:mm")}
                  {i.location && ` • ${i.location}`}
                </div>
                {i.notes && <div>{i.notes}</div>}
              </div>
            ))
          )}
        </section>
      </main>

      <BottomNav />

      <EditPersonModal
        person={person}
        open={open}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}
