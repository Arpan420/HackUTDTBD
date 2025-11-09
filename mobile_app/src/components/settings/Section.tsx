import type { FC, PropsWithChildren } from "react";

type Props = PropsWithChildren<{ title: string; description?: string }>;

export const Section: FC<Props> = ({ title, description, children }) => (
  <section className="rounded-2xl border border-neutral-200 dark:border-neutral-800 p-4 space-y-3">
    <div>
      <div className="font-semibold">{title}</div>
      {description && <div className="text-sm text-neutral-500">{description}</div>}
    </div>
    {children}
  </section>
);
