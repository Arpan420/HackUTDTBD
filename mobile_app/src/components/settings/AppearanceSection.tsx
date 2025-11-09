import type { FC } from "react";
import { useEffect, useState } from "react";
import { Section } from "./Section";
import { Toggle } from "../settings/Toggle";

export const AppearanceSection: FC = () => {
  const [isLight, setIsLight] = useState<boolean>(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "light") return true;
    if (saved === "dark") return false;
    // default to system
    return !window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isLight) {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    } else {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    }
    // nuke old keys so they never interfere again
    localStorage.removeItem("ui-white-mode");
    localStorage.removeItem("ui-force-dark");
    // force a paint so the ring-offset etc. apply immediately
    void root.offsetHeight;
  }, [isLight]);

  return (
    <Section title="Appearance" description="Theme preferences for this device.">
      <Toggle label={isLight ? "Light mode" : "Dark mode"} checked={isLight} onChange={setIsLight} />
    </Section>
  );
};
