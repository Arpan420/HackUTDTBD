import { create } from "zustand";
import { persist } from "zustand/middleware";
import dayjs from "dayjs";
import type { Person, Summary, Interaction } from "../types";

type State = {
  people: Person[];

  // mutations
  addPerson: (p: Pick<Person, "Name" | "phoneNumber">) => string;
  addSummary: (personId: string, s: Pick<Summary, "text" | "sources">) => string;
  addInteraction: (
    personId: string,
    i: Omit<Interaction, "id" | "when">
  ) => string;

  upsertPersonBasics: (personId: string, patch: Partial<Pick<Person, "Name" | "phoneNumber" | "lastSeen">>) => void;
};

const sample: Person[] = [
  {
    id: "p1",
    Name: "Sarah Patel",
    phoneNumber: "555-123-9876",
    lastSeen: dayjs().subtract(1, "day").toISOString(),
    summaries: [
      {
        id: "s1",
        text: "Discussed a project meeting; Sarah is free after 3 PM tomorrow.",
        createdAt: dayjs().subtract(1, "day").toISOString(),
      },
    ],
    interactions: [
      {
        id: "i1",
        when: dayjs().subtract(1, "day").toISOString(),
        location: "Library",
        notes: "Quick chat about timelines.",
        summaryId: "s1",
      },
    ],
  },
];

export const usePeopleStore = create<State>()(
  persist(
    (set) => ({
      people: sample,

      addPerson: ({ Name, phoneNumber }) => {
        const id = crypto.randomUUID();
        const person: Person = {
          id,
          Name,
          phoneNumber,
          summaries: [],
          interactions: [],
        };
        set((s) => ({ people: [person, ...s.people] }));
        return id;
      },

      addSummary: (personId, s) => {
        const id = crypto.randomUUID();
        const createdAt = new Date().toISOString();
        set((state) => ({
          people: state.people.map((p) =>
            p.id === personId
              ? { ...p, summaries: [{ id, createdAt, ...s }, ...p.summaries] }
              : p
          ),
        }));
        return id;
      },

      addInteraction: (personId, i) => {
        const id = crypto.randomUUID();
        const when = new Date().toISOString();
        set((state) => ({
          people: state.people.map((p) =>
            p.id === personId
              ? {
                  ...p,
                  interactions: [{ id, when, ...i }, ...p.interactions],
                  lastSeen: when,
                }
              : p
          ),
        }));
        return id;
      },

      upsertPersonBasics: (personId, patch) => {
        set((state) => ({
          people: state.people.map((p) =>
            p.id === personId ? { ...p, ...patch } : p
          ),
        }));
      },
    }),
    { name: "people-store-v1" }
  )
);
