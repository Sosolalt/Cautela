import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // TODO(design/PLAN.md §5.1 + §0.4 task 2): these hex codes are scheduled
        // for deletion. They contradict the locked deep-forest-emerald palette
        // and will be re-sourced from `design/tokens.ts` once the Art Director
        // ships the design system in Phase 5 (~Day 3). Kept temporarily because
        // components/findings-pane.tsx still consumes `bg-lane-{auto,watch,block}`.
        // Do NOT add new references to `lane.*` — use the forthcoming risk-lane
        // tokens (Clear / Escalate / Block) per §5.1.
        lane: {
          auto: "#16a34a",  // green-600  -> auto_clear   (TEMP — replace per §5.1)
          watch: "#eab308", // yellow-500 -> escalate     (TEMP — replace per §5.1)
          block: "#dc2626", // red-600    -> block        (TEMP — replace per §5.1)
        },
      },
    },
  },
  plugins: [],
};

export default config;
