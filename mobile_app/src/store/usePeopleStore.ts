import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Person, Summary, Interaction } from "../types";

type State = {
  people: Person[];
  addPerson: (p: { Name: string; phoneNumber?: string }) => void;
  updatePerson: (id: string, patch: Partial<Person>) => void; // ← NEW
  addSummary: (personId: string, s: Omit<Summary, "id" | "createdAt"> &
                                 { text: string }) => void;   // ← NEW
  addInteraction: (personId: string,
                   i: Omit<Interaction, "id">) => void;       // ← NEW
  replacePeople: (people: Person[]) => void;
};

const uid = () => Math.random().toString(36).slice(2);

export const usePeopleStore = create<State>()(
  persist(
    (set) => ({
      people: [],

      addPerson: (p) =>
        set((s) => ({
          people: [
            ...s.people,
            {
              id: uid(),
              Name: p.Name,
              phoneNumber: p.phoneNumber,
              summaries: [],
              interactions: [],
            },
          ],
        })),

      updatePerson: (id, patch) =>
        set((s) => ({
          people: s.people.map((p) =>
            p.id === id ? { ...p, ...patch } : p
          ),
        })),

      addSummary: (personId, s0) =>
        set((s) => ({
          people: s.people.map((p) =>
            p.id !== personId
              ? p
              : {
                  ...p,
                  summaries: [
                    {
                      id: uid(),
                      text: s0.text,
                      createdAt: new Date().toISOString(),
                      sources: s0.sources,
                    },
                    ...p.summaries,
                  ],
                }
          ),
        })),

      addInteraction: (personId, i0) =>
        set((s) => ({
          people: s.people.map((p) =>
            p.id !== personId
              ? p
              : {
                  ...p,
                  interactions: [
                    {
                      id: uid(),
                      when: i0.when,
                      location: i0.location,
                      notes: i0.notes,
                      summaryId: i0.summaryId,
                    },
                    ...p.interactions,
                  ],
                  lastSeen: i0.when ?? p.lastSeen,
                }
          ),
        })),

      replacePeople: (newPeople) =>
        set(() => ({
          people: newPeople,
        })),
    }),
    { name: "people-store-v1" }
  )
);
