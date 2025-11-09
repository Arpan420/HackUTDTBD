import type { FC } from "react";
import { useEffect, useState } from "react";
import { Section } from "./Section";
import { Toggle } from "../settings/Toggle";

export const AppearanceSection: FC = () => {
  const [forceDark, setForceDark] = useState<boolean>(() => {
    return localStorage.getItem("ui-force-dark") === "1";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (forceDark) {
      root.classList.add("dark");
      localStorage.setItem("ui-force-dark", "1");
    } else {
      root.classList.remove("dark");
      localStorage.removeItem("ui-force-dark");
    }
  }, [forceDark]);

  return (
    <Section title="Appearance" description="Theme preferences for this device.">
      <Toggle label="Dark mode (force)" checked={forceDark} onChange={setForceDark} />
    </Section>
  );
};
