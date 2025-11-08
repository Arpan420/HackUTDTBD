import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";

export default function Settings() {
  const reset = () => {
    localStorage.removeItem("people-store-v1");
    location.reload();
  };

  return (
    <div className="pb-20">
      <TopBar title="Settings" />
      <main className="max-w-screen-sm mx-auto p-4 space-y-4">
        <section className="rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
          <div className="font-semibold">Data</div>
          <button
            onClick={reset}
            className="px-3 py-2 rounded-lg bg-red-600 text-white text-sm"
          >
            Reset local demo data
          </button>
        </section>

        <section className="rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
          <div className="font-semibold">AI Integration (coming soon)</div>
          <div className="text-sm text-neutral-500">
            When your pipeline emits events like <code>summary.created</code> or{" "}
            <code>interaction.logged</code>, call the corresponding store methods to update the UI.
          </div>
        </section>
      </main>
      <BottomNav />
    </div>
  );
}
