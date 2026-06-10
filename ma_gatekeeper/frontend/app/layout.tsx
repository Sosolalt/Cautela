import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Cautela — M&A Due Diligence",
  description:
    "M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  // Dark-default per the Documentary-Brutalism brief (canonical:
  // design/claude-design-output/README.md §Color). The body renders on the
  // locked --surface (#0B0B0C, slightly-warm near-black — NEVER #000000) with
  // --ink (#ECECEA) text. Light-mode parity opts in via `<html data-theme="light">`.
  // Existing review-app panes (app/page.tsx) set `bg-white` explicitly so the
  // dark body backdrop only shows through where children don't paint a surface.
  return (
    <html lang="en">
      <body className="h-full bg-surface text-ink antialiased font-body">
        {children}
      </body>
    </html>
  );
}
