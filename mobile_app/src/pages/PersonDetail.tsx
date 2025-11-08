import { useParams } from "react-router-dom";
import { usePeopleStore } from "../store/usePeopleStore";
import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";
import { SummaryCard } from "../components/SummaryCard";
import dayjs from "dayjs";

export default function PersonDetail() {
  const { id } = useParams();
  const person = usePeopleStore((s) => s.people.find((p) => p.id === id));

  if (!person) return <div className="p-4">Person not found.</div>;

  return (
    <div className="pb-20">
      <TopBar title={person.Name} />
      <main className="max-w-screen-sm mx-auto p-4 space-y-6">
        <section className="rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4 text-sm">
          <div>Phone: {person.phoneNumber ?? "—"}</div>
          <div>
            Last Seen:{" "}
            {person.lastSeen ? dayjs(person.lastSeen).format("MMM D, YYYY") : "—"}
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="font-semibold text-sm">AI Summaries</h3>
          {person.summaries.length === 0 && (
            <div className="text-sm text-neutral-500">No summaries yet.</div>
          )}
          {person.summaries.map((s) => (
            <SummaryCard key={s.id} s={s} />
          ))}
        </section>

        <section className="space-y-2">
          <h3 className="font-semibold text-sm">Recent Interactions</h3>
          {person.interactions.length === 0 && (
            <div className="text-sm text-neutral-500">No interactions logged.</div>
          )}
          {person.interactions.map((i) => (
            <div
              key={i.id}
              className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-3"
            >
              <div className="text-xs text-neutral-500">
                {dayjs(i.when).format("MMM D, HH:mm")}
                {i.location ? ` • ${i.location}` : ""}
              </div>
              {i.notes && <div className="text-sm mt-1">{i.notes}</div>}
            </div>
          ))}
        </section>
      </main>
      <BottomNav />
    </div>
  );
}
