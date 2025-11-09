// usePeopleStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Person, Summary, Interaction } from "../types";
import { supabase } from "../lib/supabaseClient";

type State = {
  people: Person[];
  addPerson: (p: { Name: string; phoneNumber?: string }) => void;
  updatePerson: (id: string, patch: Partial<Person>) => void;
  addSummary: (personId: string, s: Omit<Summary, "id" | "createdAt"> & { text: string }) => void;
  addInteraction: (personId: string, i: Omit<Interaction, "id">) => void;
  replacePeople: (people: Person[]) => void;
  fetchPeople: () => Promise<void>;
  deletePerson: (id: string) => Promise<void>;
};

const uid = () => Math.random().toString(36).slice(2);

export const usePeopleStore = create<State>()(
  persist(
    (set, get) => ({
      people: [],

      fetchPeople: async () => {
        // Faces
        const { data: faceRows, error: facesError } = await supabase
          .from("faces")
          .select("person_id")
          .returns<{ person_id: string }[]>();   // <- helps TS

        if (facesError) {
          console.error("Error fetching faces:", facesError);
          return;
        }
        const faces = faceRows ?? []; // <- normalize null to []

        // Summaries
        const { data: summaryRows, error: summaryError } = await supabase
          .from("summaries")
          .select("person_id, summary_text")
          .returns<{ person_id: string; summary_text: string }[]>();

        if (summaryError) {
          console.error("Error fetching summaries:", summaryError);
          return;
        }
        const summaries = summaryRows ?? []; // <- normalize null to []

        // Build a map person_id -> Summary[]
        const summaryMap: Record<string, Summary[]> = {};
        for (const row of summaries) {
          (summaryMap[row.person_id] ??= []).push({
            id: Math.random().toString(36).slice(2),
            text: row.summary_text,
            createdAt: new Date().toISOString(),
            sources: [],
          });
        }

        // Map to your Person[]
        const mappedPeople: Person[] = faces.map((row) => ({
          id: row.person_id,
          Name: row.person_id,
          phoneNumber: undefined,
          summaries: summaryMap[row.person_id] ?? [],
          interactions: [],
        }));

        set({ people: mappedPeople });
    },

      
      deletePerson: async (id: string) => {
        const person = get().people.find((p) => p.id === id);
        if (!person) return;

        const name = person.Name; // faces.person_id

        const { error: sErr } = await supabase
          .from("summaries")
          .delete()
          .eq("person_id", name);
        if (sErr) {
          console.error("Delete summaries failed:", sErr);
          throw sErr;
        }

        const { error: fErr } = await supabase
          .from("faces")
          .delete()
          .eq("person_id", name);
        if (fErr) {
          console.error("Delete face failed:", fErr);
          throw fErr;
        }

        set((s) => ({ people: s.people.filter((p) => p.id !== id) }));
      },

      // … keep your other actions unchanged …
      addPerson: (p) =>
        set((s) => ({
          people: [
            ...s.people,
            {
              id: p.Name,
              Name: p.Name,
              phoneNumber: p.phoneNumber,
              summaries: [],
              interactions: [],
            },
          ],
        })),

      updatePerson: (id, patch) =>
        set((s) => ({
          people: s.people.map((p) => (p.id === id ? { ...p, ...patch } : p)),
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

      replacePeople: (newPeople) => set(() => ({ people: newPeople })),
    }),
    { name: "people-store-v1" }
  )
);
