import type { FC, ChangeEvent } from "react";
import { Section } from "./Section";
import { Button } from "../ui/Button";
import { usePeopleStore } from "../../store/usePeopleStore";
import type { Person } from "../../types";

function download(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name.endsWith(".json") ? name : `${name}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export const DataSection: FC = () => {
  const people = usePeopleStore((s) => s.people);
  const replacePeople = usePeopleStore((s) => s.replacePeople);

  const onExport = () =>
    download("people-backup", { exportedAt: new Date().toISOString(), people });

  const onImport = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed.people ?? parsed)) {
        alert("Invalid file format.");
        return;
      }
      const list: Person[] = Array.isArray(parsed) ? parsed : parsed.people;
      replacePeople(list);
      alert(`Imported ${list.length} people.`);
    } catch {
      alert("Failed to import JSON.");
    } finally {
      e.target.value = "";
    }
  };

  const onReset = () => {
    localStorage.removeItem("people-store-v1");
    location.reload();
  };

  return (
    <Section title="Data" description="Backup or restore local demo data.">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={onExport}>
          Export JSON
        </Button>

        <Button
          variant="secondary"
          upload
          inputProps={{
            accept: "application/json",
            onChange: onImport,
          }}
        >
          Import JSON
        </Button>

        <Button variant="danger" onClick={onReset}>
          Reset Local Data
        </Button>
      </div>
    </Section>
  );
};
