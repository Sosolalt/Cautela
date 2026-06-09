"use client";

import dynamic from "next/dynamic";

// The hero is a WebGL (Three.js) surface — never server-render it. `ssr: false`
// keeps three out of the server bundle and avoids a canvas hydration flash.
// Loaded from a Client Component so the `ssr: false` form is valid across Next
// 14/15. Page metadata is owned by app/layout.tsx. The review tool now lives at
// /review (linked from the hero's primary CTA).
const Hero = dynamic(() => import("@/components/hero/hero"), {
  ssr: false,
  loading: () => <div style={{ height: "100vh", background: "var(--surface)" }} />,
});

export default function HomePage() {
  return <Hero />;
}
