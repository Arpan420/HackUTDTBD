import type { FC } from "react";

type Props = {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
};

export const Toggle: FC<Props> = ({ label, checked, onChange }) => {
  return (
    <label className="flex items-center justify-between gap-2 py-1">
      <span className="text-sm">{label}</span>

      <input
        type="checkbox"
        className="h-5 w-10"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
};
