/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a self-contained server bundle (.next/standalone/server.js) so the
  // Cloud Run image can run `node server.js` without node_modules. The
  // standalone server honors the PORT env var that Cloud Run injects.
  output: "standalone",
  reactStrictMode: true,
  // Same-origin proxy to the Phoenix REST API so the browser can fetch spans/
  // experiments WITHOUT CORS (phoenix-prod emits no Access-Control-Allow-Origin
  // and 405s OPTIONS preflight; a cross-origin fetch is otherwise blocked).
  // API JSON only — we do NOT proxy the Phoenix SPA here (its assets use
  // absolute /assets/... paths that would break under a subpath); the board is
  // embedded via a direct cross-origin <iframe> in components/phoenix-board.tsx,
  // which works because Phoenix sends no X-Frame-Options / frame-ancestors CSP.
  // Target is overridable at server start via PHOENIX_PROXY_TARGET.
  async rewrites() {
    const phoenix =
      process.env.PHOENIX_PROXY_TARGET ??
      "https://phoenix-prod-eqxulvtmha-uc.a.run.app";
    return [{ source: "/phoenix-api/:path*", destination: `${phoenix}/v1/:path*` }];
  },
  // react-pdf ships pdfjs as ESM-only; Next needs to know not to transpile it.
  transpilePackages: ["react-pdf", "pdfjs-dist"],
  webpack: (config) => {
    // canvas is a Node-only optional dep pdfjs tries to require; alias it out
    // so the client bundle resolves.
    config.resolve.alias.canvas = false;
    // NOTE: the pdfjs *worker* is no longer bundled via
    // `new URL(..., import.meta.url)` — that made webpack emit it as an asset
    // and run it through Terser, which crashed on the worker's ESM
    // `import`/`export` ("cannot be used outside of module code") and broke
    // `next build`. It is now served as a static file from /public; see
    // components/pdf-pane.tsx and the `copy-pdf-worker` step in package.json.
    return config;
  },
};

export default nextConfig;
