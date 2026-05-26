import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "M&A Due Diligence Gatekeeper",
  description: "Auditable AI contract review with Arize Phoenix observability.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="h-full bg-neutral-50 text-neutral-900 antialiased">
        {children}
      </body>
    </html>
  );
}
