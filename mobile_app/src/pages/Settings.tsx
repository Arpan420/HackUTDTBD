import { TopBar } from "../components/TopBar";
import { BottomNav } from "../components/BottomNav";
import { AppearanceSection } from "../components/settings/AppearanceSection";
import { DataSection } from "../components/settings/DataSection";

export default function Settings() {
  return (
    <div className="pb-20">
      <TopBar title="Settings" />
      <main className="max-w-screen-sm mx-auto p-4 space-y-4">
        <AppearanceSection />
        <DataSection />
      </main>
      <BottomNav />
    </div>
  );
}
