# Frontend — M&A Due Diligence Gatekeeper

Next.js 14 (App Router) + Tailwind 3 three-pane review surface (plan §7 D15).

```
┌───────────────┬─────────────┬───────────────┐
│   PDF viewer  │  Findings   │   Phoenix     │
│   react-pdf   │  list       │   trace       │
│   (left)      │  (center)   │   (right)     │
└───────────────┴─────────────┴───────────────┘
```

State shared across panes is a single `selectedFindingId`. Clicking a
finding in the center pane (a) scrolls the PDF and (b) navigates the
Phoenix iframe to the corresponding trace. The reverse direction
(PDF click → finding select) lands on D15 as a 1-day lookup using the
`pdf_bbox` already populated by the Parser agent.

## Quickstart

```bash
cp .env.example .env.local      # fill in NEXT_PUBLIC_API_BASE + Phoenix URL
npm install
npm run dev                     # http://localhost:3000
```

The backend FastAPI service must be running on `NEXT_PUBLIC_API_BASE`
(default `http://localhost:8080`). Start it from `ma_gatekeeper/`:

```bash
uvicorn agent.server:app --port 8080
```

## Architecture notes

- **No EventSource.** `/review-by-deal` requires the `X-Demo-Passcode`
  header, which `EventSource` cannot send. `lib/api.ts` uses fetch +
  a `ReadableStream` reader to parse SSE frames manually.
- **PDF worker pin.** `react-pdf` requires the bundled pdfjs worker to
  match `pdfjs-dist` exactly — see the pinned versions in
  `package.json`. Bumping one without the other crashes with an
  "API/Worker version mismatch" error at runtime.
- **Phoenix iframe sandbox.** The trace pane uses
  `sandbox="allow-scripts allow-same-origin allow-popups"`. Drop
  `allow-same-origin` if you reverse-proxy Phoenix through a
  third-party domain — Phoenix needs same-origin storage access.
- **No auth on the browser side.** The `NEXT_PUBLIC_DEMO_PASSCODE` is
  visible to anyone who inspects the bundle — that's intentional; the
  passcode is a "make scrapers pay attention" gate, not auth. The
  security-sensitive route is `/reflect`, which is OIDC-protected and
  unreachable from the browser.

## What still needs doing on D15-D17

Per plan §7 / HANDOFF.md:

- `RiskFinding` does not yet carry `page` + `pdf_bbox` — thread them
  through the SSE stream from the agent (the Clause has them, the
  Finding doesn't).
- Add `/pdf-proxy/{deal_id}` to `agent/server.py` so the PDF pane has
  a URL to load (the file lives in tempfs after EdgarTools fetches it).
- shadcn/ui polish: replace the raw `<select>` with a Combobox; add
  loading skeletons; add a "auto-promoted" toast that fires when the
  Reflector promotes a candidate prompt mid-demo (plan §8).
- Reverse sync: click clause in PDF → select matching finding using
  `pdf_bbox` containment.
