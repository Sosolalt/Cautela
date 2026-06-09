// @ts-nocheck
/* =============================================================
   Hero — Three.js scene.
   Documentary Brutalism: pile lives inside the right 45vw canvas
   wrapper. Verdict reticle dot is in 3D; the trace hairline is an
   SVG <line> projected from the 3D dot's screen position to the
   Phoenix Span ID anchor in the DOM bottom-left.

   The page-curl vertex math, pile/staple/paper material logic
   and texture pipeline are unchanged from the previous revision.

   PORT NOTE (React/Next integration): the original was a self-running
   IIFE that read three DOM nodes by id and a global `THREE`. It is now an
   exported `initHeroScene({canvas, svgLine, spanAnchor})` that takes the
   nodes as args, imports `three` as a module, and returns a `dispose()`
   for React unmount. The animation math / geometry / easing / texture
   pipeline are byte-for-byte unchanged. The ONLY edits to the body are:
   (1) capturing the RAF id at the two `requestAnimationFrame(tick)` sites
   so the loop is cancellable, (2) a reduced-motion early path that pins
   one resolved frame and stops, (3) dispose/teardown, (4) NODE_ENV-gating
   the debug globals.
   ============================================================= */

import * as THREE from "three";

export function initHeroScene(opts: {
  canvas: HTMLCanvasElement;
  svgLine: SVGLineElement;
  spanAnchor: HTMLElement;
}): () => void {
  const canvas      = opts.canvas;
  const svgLine     = opts.svgLine;
  const spanAnchor  = opts.spanAnchor;
  const reduced     = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Reduced-motion: pin to the verdict-hold window (valid range [3.65, 5.80]s
  // of the 7s LOOP — past flip+dot+line, before fade) and render one frame.
  const REDUCED_T = 4.5;
  let rafId = 0;
  let disposed = false;
  let resizeObserver: ResizeObserver | undefined;

  // ---------- Constants ----------
  const PAGE_W = 8.0;
  const PAGE_L = 11.0;
  const STACK_COUNT = 25;
  const PAGE_THICK = 0.012;     // actual box thickness — gives the pile real volume

  // Staple pivot inset — the staple (and therefore the page-flip HINGE) sits
  // this far IN from the top-left corner, not on the raw paper edge, so the
  // turn pivots around a believable bound point. Used by: the flip geometry
  // origin translate, the staple ASSET placement, and the anti-seesaw lift.
  const STAPLE_INSET_X = 0.60;   // in from the LEFT edge — nudged toward the corner
  const STAPLE_INSET_Z = 0.28;   // in from the TOP edge — nudged toward the corner
  const STACK_GAP  = 0.014;     // y-spacing between page centers (≥ thickness so plies pop)
  // Loop: 0.0–2.5 page-flip → 2.5–2.7 dot snap → 2.7–3.25 line shoot
  //       → 3.25–5.8 verdict held → 5.8–6.5 fade & reset.
  const LOOP = 7.0;             // seconds (+0.5 to preserve verdict hold after longer flip)
  const FLIP_DUR = 2.9;         // +0.5s — gives the slower easeInOutQuint room to breathe
  const ACCENT_VERM = 0xE63D2F;
  const PAPER_HEX = '#EFE9D9';
  const INK_HEX   = '#1A1916';
  // Highlight on flagged clause — switched to vermillion-tinted (was champagne)
  const HILITE_BG = 'rgba(230,61,47,0.20)';
  const HILITE_BAR = '#E63D2F';

  // ---------- Easings ----------
  const easeInOutCubic = t => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3)/2;
  const easeOutCubic   = t => 1 - Math.pow(1 - t, 3);
  const easeOutExpo    = t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
  const easeInCubic    = t => t * t * t;
  const clamp01        = t => Math.max(0, Math.min(1, t));

  // ---------- Three.js setup ----------
  const cw = () => canvas.clientWidth;
  const ch = () => canvas.clientHeight;

  const scene = new THREE.Scene();

  // ---------- Orthographic isometric camera ----------
  // Strict parallel projection: no perspective foreshortening, so the
  // stack reads as a true 3D volume rather than a vanishing wedge.
  // Tilted forward enough to clearly see the top page, but kept high enough
  // that the ply edges along the right and front faces stay legible.
  // Perspective rig — "flat on the desk" bottom-right composition. The camera
  // sits HIGH with a steep downward pitch and a low look-target, so the stack
  // reads as lying flat on a surface beneath us (the tilt is the viewing
  // pitch, not an off-plane rotation of the paper). Framing seats the stack
  // right and small, leaving the left clear for the headline and the top-right
  // clear for the page-flip arc.
  const CAM_FOV   = 32;
  const CAM_POS   = [12.0, 11.5, 8.0];
  const CAM_LOOK  = [13.0, -1.2, 0];
  const buildPersp = () => {
    const c = new THREE.PerspectiveCamera(CAM_FOV, cw() / ch(), 0.1, 1000);
    c.position.set(CAM_POS[0], CAM_POS[1], CAM_POS[2]);
    c.lookAt(CAM_LOOK[0], CAM_LOOK[1], CAM_LOOK[2]);
    return c;
  };
  let camera = buildPersp();

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(cw(), ch(), false);
  renderer.setClearColor(0x000000, 0);          // transparent → blends over --surface
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  // ---------- Real shadow mapping (photorealistic pass) ----------
  // Hard, high-resolution cast shadows define the page edges and let the
  // rearing flip-page throw a dramatic shadow across the dossier.
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  // ---------- Stack yaw delta ----------
  // The stack now faces the viewer 20° more than the previous revision.
  // This SAME delta is applied to the directional-light rig below, so the
  // crisp shadows and contrast across the paper read identically after the
  // rotation (a directional light only cares about its DIRECTION — rotating
  // each light's position about world-Y by the same angle rotates the
  // light→origin direction by that angle, exactly tracking the stack).
  const STACK_YAW_DELTA = 20 * Math.PI / 180;   // +20° CCW about world Y

  // ---------- Lighting (photorealistic pass) ----------
  // Deep, low ambient so shadows fall away into the black UI background; a
  // dedicated high-resolution shadow-casting key (added after the geometry,
  // parented to `world`) supplies the premium warm-off-white desk-lamp light
  // and the hard cast shadows. The directional lights here are now FILL/RIM
  // only — they shape the paper without washing the contrast out.
  const ambient = new THREE.AmbientLight(0x1a160f, 0.10);
  scene.add(ambient);

  // Hemisphere: warm sky, near-black warm ground — a whisper of bounce on the
  // page underside without lifting the shadows.
  const hemi = new THREE.HemisphereLight(0xffe7c2, 0x0a0805, 0.14);
  scene.add(hemi);

  const key  = new THREE.DirectionalLight(0xfff4e6, 0.40);     // soft warm side-fill (shadow key added below)
  key.position.set(-5, 12, -11);                              // front-left, near (staple) side

  const fill = new THREE.DirectionalLight(0xc9b89c, 0.22);     // warm low fill (was cool)
  fill.position.set(-9, 5, 6);

  const rim  = new THREE.DirectionalLight(0xfff3e2, 0.55);     // soft rim — catches ply edges
  rim.position.set(-10, 4, 5);

  const edge = new THREE.DirectionalLight(0xE63D2F, 0.10);     // faint brand accent on far edge
  edge.position.set(-12, 1, 4);

  // Subtle warm bounce from below — underside of the flipping page.
  const bounce = new THREE.DirectionalLight(0xc8bda0, 0.22);
  bounce.position.set(2, -6, -3);

  // Warm pool over the NEAR (heading) corner — inverse-square falloff carries
  // the brightness gradient from the near edge into shadow at the far end.
  const pool = new THREE.PointLight(0xfff0d6, 2.4, 26, 1.4);
  pool.position.set(4.6, 7.5, -6.5);
  scene.add(pool);

  // Directional rig — yaw-tracks the stack (lightRig.rotation.y = world yaw)
  // so the warm key keeps grazing the same heading/staple edge and the
  // ply-wall shadows stay crisp after the stack is re-twisted.
  const lightRig = new THREE.Group();
  lightRig.rotation.y = -0.78;
  lightRig.add(key, fill, rim, edge, bounce);
  scene.add(lightRig);

  // Live-tuning handle (dev only).
  if (process.env.NODE_ENV !== 'production') {
    window.__L = { ambient, hemi, key, fill, rim, edge, bounce, pool };
  }

  // ---------- World root — sit the stack hard against the right margin ----------
  // Yawed an extra +20° (STACK_YAW_DELTA) so the stack faces the camera more
  // ---------- World root — "close macro, steep twist" placement ----------
  // Camera pushed in CLOSE and LOW (12, 11, 8) with a telephoto-ish 32° FOV so
  // the dossier reads as a massive foreground object with flattened
  // perspective lines. The frustum stays centered on the stack (cam.x 12 →
  // look.x 13) so there is no keystone "sliding" distortion. A steeper ~44.7°
  // clockwise yaw gives the dramatic diagonal twist; the counter-roll
  // (+rotation.z) and nose-up pitch (−rotation.x) are RETAINED to keep the
  // corners from drooping. The stack is seated so the staple/top-left corner
  // anchors in the open space just right of the "Every verdict, traced."
  // headline; the bottom and right edges run massively off-screen by design.
  const world = new THREE.Group();
  world.position.set(18.0, -4.5, -0.6);        // staple anchored right of headline · massive off-screen spill
  world.rotation.set(-0.05, -0.78, 0.25);      // slight pitch (restores edge thickness) · ≈44.7° yaw · counter-roll to level
  scene.add(world);

  // (No floor — canvas is transparent and blends over --surface.)

  // ---------- Page content data (4 chapters) ----------
  // Each entry drives ONE crisp Canvas2D texture + a matching emissive map
  // (red highlight only), and the Phoenix-trace UI card. No PNGs — all
  // typography is vector-drawn into an off-screen canvas at boot.
  const PAGES = [
    {
      heading: 'ARTICLE I — DEFINITIONS & INTERPRETATIONS',
      sectionSub: 'Section 1.4 — Defined Terms; Material Adverse Effect',
      docMeta: 'EX-2.1 · P. 12 OF 312 · EFFECTIVE 2026-05-27',
      footPage: 'P. 12 / 312',
      targetWord: 'disproportionate',
      clauses: [
        { num: '1.1', text: '"Agreement" means this Stock Purchase Agreement, together with all Exhibits, Schedules, and the Company Disclosure Schedule, as the same may be amended, restated, or otherwise modified from time to time in accordance with its terms.' },
        { num: '1.2', text: 'This Agreement and all matters arising out of or relating hereto shall be governed by the laws of the State of Delaware, without giving effect to any choice-of-law principles that would require the application of another jurisdiction.' },
        { num: '1.4(b)', text: 'Material Adverse Effect: Any event, change, or circumstance that, individually or in the aggregate, has a disproportionate impact on the target\u2019s operational capabilities, excluding industry-wide market fluctuations.', flagged: true },
        { num: '1.5', text: 'References to "the Parties" mean the Buyer and the Seller collectively, and "Party" means either of them; words importing the singular include the plural, and headings are for convenience only.' },
        { num: '1.6', text: 'Unless the context otherwise requires, references to Sections, Articles, Exhibits, and Schedules are to the corresponding provisions of this Agreement, and the word "including" shall be deemed to be followed by "without limitation."' }
      ],
      spanId: 'phoenix:span:1a4b-d2c0-7e93-0f12',
      clauseLabel: 'Clause 1.4(b)',
      clauseTag: 'Adverse effect',
      ci: 'Cluster-bootstrap LB · 0.91'
    },
    {
      heading: 'ARTICLE II — THE TRANSACTION & PURCHASE PRICE',
      sectionSub: 'Section 2.3 — Closing; Escrow; Wire Transfers',
      docMeta: 'EX-2.1 · P. 88 OF 312 · EFFECTIVE 2026-05-27',
      footPage: 'P. 88 / 312',
      targetWord: 'Escrow',
      clauses: [
        { num: '2.1', text: 'The closing of the transactions contemplated by this Agreement (the "Closing") shall take place remotely via the electronic exchange of documents at 10:00 a.m. Eastern Time on the third Business Day following satisfaction of the conditions in Article VII.' },
        { num: '2.2', text: 'At the Closing, the Buyer shall pay the Purchase Price by wire transfer of immediately available funds to the accounts designated by the Seller in writing not less than two Business Days prior to the Closing Date.' },
        { num: '2.2(b)', text: 'Each wire transfer shall be made in United States dollars to the account specified in the Funds Flow Memorandum delivered by the Seller, and shall be deemed received only upon written confirmation by the receiving bank.' },
        { num: '2.3(a)', text: 'Escrow Funds: The Buyer shall deposit $15,000,000 into the Escrow Account to satisfy potential indemnification claims related to the pending litigation disclosed in Schedule 2.', flagged: true },
        { num: '2.4', text: 'The authorized capitalization of the Company consists of the shares set forth in the Disclosure Schedule, all of which are duly authorized, validly issued, fully paid, and nonassessable, and free of any preemptive rights.' }
      ],
      spanId: 'phoenix:span:2c3d-9a17-4b56-8e21',
      clauseLabel: 'Clause 2.3(a)',
      clauseTag: 'Escrow · indemnity',
      ci: 'Cluster-bootstrap LB · 0.97'
    },
    {
      heading: 'ARTICLE III — COVENANTS & AGREEMENTS',
      sectionSub: 'Section 3.1 — Conduct of Business; Non-Solicitation',
      docMeta: 'EX-2.1 · P. 154 OF 312 · EFFECTIVE 2026-05-27',
      footPage: 'P. 154 / 312',
      targetWord: 'consent',
      clauses: [
        { num: '3.1(a)', text: 'During the Interim Period, the Seller shall use commercially reasonable efforts to carry on the business in the ordinary course and to preserve intact its present organization, assets, and relationships with customers, suppliers, and employees.' },
        { num: '3.1(c)', text: 'Conduct of Business: The Seller shall not, without prior written consent, enter into any material contract or incur any debt exceeding $500,000 outside the ordinary course of business.', flagged: true },
        { num: '3.2', text: 'Non-Solicitation: For a period of twenty-four (24) months following the Closing, the Seller shall not, directly or indirectly, solicit for employment any employee of the Company whose annual base compensation exceeds $150,000.' },
        { num: '3.3', text: 'Public Announcements: No Party shall issue any press release or make any public statement concerning this Agreement without the prior written approval of the other Party, except as required by applicable law.' },
        { num: '3.4', text: 'Confidentiality: Each Party shall hold in strict confidence all non-public information concerning the other Party obtained in connection with this Agreement, and shall use such information solely for the purpose of consummating the transactions contemplated hereby.' }
      ],
      spanId: 'phoenix:span:3e8f-6b42-1d09-5a73',
      clauseLabel: 'Clause 3.1(c)',
      clauseTag: 'Conduct of business',
      ci: 'Cluster-bootstrap LB · 0.89'
    },
    {
      heading: 'ARTICLE IV — REPRESENTATIONS & WARRANTIES',
      sectionSub: 'Section 4.2 — Material Adverse Effect; Knowledge Qualifiers',
      docMeta: 'EX-2.1 · P. 47 OF 312 · EFFECTIVE 2026-05-27',
      footPage: 'P. 47 / 312',
      targetWord: 'environmental',
      clauses: [
        { num: '4.2(a)', text: 'Except as set forth in Section 4.2(a) of the Company Disclosure Schedule, since the date of the most recent audited financial statements through the date of this Agreement, there has not been any change, effect, event, occurrence, state of facts, or development that, individually or in the aggregate, has had or would reasonably be expected to have a Material Adverse Effect.' },
        { num: '4.2(b)', text: 'The Company has not entered into any contract, agreement, commitment, arrangement, or understanding (whether written or oral) that requires the Company or any of its Subsidiaries to make payments in excess of $5,000,000 in any fiscal year, other than as set forth in Section 4.2(b) of the Disclosure Schedule.' },
        { num: '4.2(c)', text: 'Notwithstanding anything to the contrary herein, the Company makes no representation or warranty as to any environmental matter, employee benefit plan, intellectual property right, or tax matter arising prior to the Closing Date, and Buyer shall have no recourse with respect to such matters except as expressly provided in Article VIII.', flagged: true },
        { num: '4.2(d)', text: 'Each of the representations and warranties of the Company contained in this Agreement shall be deemed to be qualified in their entirety by reference to the Knowledge of the Company, as such term is defined in Annex A hereto, and no representation or warranty shall be construed as absolute.' },
        { num: '4.2(e)', text: 'Buyer acknowledges that it has conducted its own independent investigation, review, and analysis of the business, operations, assets, liabilities, results of operations, financial condition, and prospects of the Company.' }
      ],
      spanId: 'phoenix:span:7f3a-c2b1-9d04-8e57',
      clauseLabel: 'Clause 4.2(c)',
      clauseTag: 'Knowledge carve-out',
      ci: 'Cluster-bootstrap LB · 0.94'
    }
  ];

  // ---------- Page texture factories ----------
  // Builds, for ONE page object: a crisp Canvas2D contract texture, AND a
  // matching emissive map — black everywhere except the flagged clause, where
  // the highlight band + clause text are painted in red so they self-illuminate
  // (the "emissive ink" that keeps the flag glowing while the page is in shadow).
  function buildPageTexture(page) {
    const C_W = 1024, C_H = 1400;
    const cv = document.createElement('canvas');
    cv.width = C_W; cv.height = C_H;
    const ctx = cv.getContext('2d');

    // Emissive companion canvas — starts pure black (no glow anywhere).
    const ev = document.createElement('canvas');
    ev.width = C_W; ev.height = C_H;
    const ectx = ev.getContext('2d');
    ectx.fillStyle = '#000';
    ectx.fillRect(0, 0, C_W, C_H);

    // Paper base — cool, modern off-white (laser-printed M&A due diligence look)
    const grd = ctx.createLinearGradient(0, 0, C_W, C_H);
    grd.addColorStop(0, '#F4F6F8');
    grd.addColorStop(1, '#E4E7EB');
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, C_W, C_H);

    // Grain
    ctx.fillStyle = 'rgba(20,24,30,0.04)';
    for (let i = 0; i < 4500; i++) ctx.fillRect(Math.random()*C_W, Math.random()*C_H, 1, 1);

    // Court margin rule
    ctx.fillStyle = '#C5CAD2';
    ctx.fillRect(115, 50, 1, C_H - 100);

    // Line numbers on the page itself
    ctx.fillStyle = '#A8AEB7';
    ctx.font = '11px "Geist Mono","IBM Plex Mono",monospace';
    ctx.textAlign = 'right';
    for (let i = 1; i <= 48; i++) ctx.fillText(String(i).padStart(2, '0'), 100, 110 + (i - 1) * 26);

    // Doc ID top-right
    ctx.fillStyle = '#7B8290';
    ctx.font = '11px "Geist Mono","IBM Plex Mono",monospace';
    ctx.textAlign = 'right';
    ctx.fillText(page.docMeta, 980, 64);

    // Article head
    ctx.fillStyle = INK_HEX;
    ctx.font = '700 22px "Newsreader",Georgia,serif';
    ctx.textAlign = 'left';
    ctx.fillText(page.heading, 160, 140);

    ctx.fillStyle = '#6C7280';
    ctx.font = 'italic 16px "Newsreader",Georgia,serif';
    ctx.fillText(page.sectionSub, 160, 168);

    const clauses = page.clauses;

    // Draws wrapped clause body onto ANY 2D context (main OR emissive). When a
    // wopts.targetWord is supplied, captures the on-canvas centre of that word
    // (used to anchor the verdict-reticle dot in 3D). Pass wopts=null to just
    // paint (e.g. the red emissive re-draw of the flagged clause).
    function wrapText(dctx, str, x, y, maxW, lh, wopts) {
      const words = str.split(' ');
      let line = '', cy = y;
      for (let i = 0; i < words.length; i++) {
        const test = line + words[i] + ' ';
        const wMeas = dctx.measureText(test).width;
        if (wMeas > maxW && i > 0) {
          dctx.fillText(line, x, cy);
          if (wopts && wopts.targetWord && line.includes(wopts.targetWord) && !wopts.captured) {
            const idx = line.indexOf(wopts.targetWord);
            const before = dctx.measureText(line.slice(0, idx)).width;
            const wW = dctx.measureText(wopts.targetWord).width;
            wopts.targetPos = { x: x + before + wW/2, y: cy + 2, w: wW };
            wopts.captured = true;
          }
          line = words[i] + ' ';
          cy += lh;
        } else {
          line = test;
        }
      }
      dctx.fillText(line, x, cy);
      if (wopts && wopts.targetWord && line.includes(wopts.targetWord) && !wopts.captured) {
        const idx = line.indexOf(wopts.targetWord);
        const before = dctx.measureText(line.slice(0, idx)).width;
        const wW = dctx.measureText(wopts.targetWord).width;
        wopts.targetPos = { x: x + before + wW/2, y: cy + 2, w: wW };
        wopts.captured = true;
      }
      return cy + lh;
    }

    let y = 210;
    let targetWordPos = null;

    for (const c of clauses) {
      const startY = y;
      ctx.font = '14px "Newsreader",Georgia,serif';
      const measureCtx = document.createElement('canvas').getContext('2d');
      measureCtx.font = ctx.font;
      const avgW = measureCtx.measureText('m').width;
      const cols = Math.floor(720 / avgW);
      const approxLines = Math.ceil((c.num.length + 2 + c.text.length) / cols);
      const blockH = approxLines * 19 + 8;

      if (c.flagged) {
        // Vermillion-tinted highlight band on the visible texture …
        ctx.fillStyle = HILITE_BG;
        ctx.fillRect(148, startY - 18, 820, blockH + 8);
        ctx.fillStyle = HILITE_BAR;
        ctx.fillRect(148, startY - 18, 3, blockH + 8);
        // … and the SAME geometry painted onto the emissive map so it glows.
        ectx.fillStyle = '#3a0b07';
        ectx.fillRect(148, startY - 18, 820, blockH + 8);
        ectx.fillStyle = '#E63D2F';
        ectx.fillRect(148, startY - 18, 3, blockH + 8);
      }

      ctx.fillStyle = INK_HEX;
      ctx.font = '700 14px "Newsreader",Georgia,serif';
      ctx.fillText(c.num, 160, y);
      const numW = ctx.measureText(c.num).width;
      if (c.flagged) {
        ectx.fillStyle = '#d8362a';
        ectx.font = '700 14px "Newsreader",Georgia,serif';
        ectx.fillText(c.num, 160, y);
      }

      ctx.font = '14px "Newsreader",Georgia,serif';
      ctx.fillStyle = INK_HEX;
      const opts2 = c.flagged ? { targetWord: page.targetWord, captured: false } : null;
      const yEnd = wrapText(ctx, c.text, 160 + numW + 8, y, 720 - numW, 19, opts2);
      if (c.flagged) {
        // Re-draw the flagged clause body in red on the emissive map (same coords).
        ectx.font = '14px "Newsreader",Georgia,serif';
        ectx.fillStyle = '#c43024';
        wrapText(ectx, c.text, 160 + numW + 8, y, 720 - numW, 19, null);
      }
      if (opts2 && opts2.targetPos) targetWordPos = opts2.targetPos;

      y = yEnd + 14;
    }

    // Foot rule
    ctx.fillStyle = '#C5CAD2';
    ctx.fillRect(115, C_H - 70, C_W - 230, 1);
    ctx.font = '10px "Geist Mono",monospace';
    ctx.fillStyle = '#7B8290';
    ctx.textAlign = 'left';
    ctx.fillText('EX-2.1', 160, C_H - 50);
    ctx.textAlign = 'right';
    ctx.fillText(page.footPage, 980, C_H - 50);

    const tex = new THREE.CanvasTexture(cv);
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tex.colorSpace = THREE.SRGBColorSpace;
    const emis = new THREE.CanvasTexture(ev);
    emis.anisotropy = renderer.capabilities.getMaxAnisotropy();
    emis.colorSpace = THREE.SRGBColorSpace;
    return {
      texture: tex,
      emissiveMap: emis,
      target: targetWordPos ? {
        local: new THREE.Vector3(
          (targetWordPos.x / C_W - 0.5) * PAGE_W,
          0.001,
          (targetWordPos.y / C_H - 0.5) * PAGE_L
        )
      } : null
    };
  }

  // Build all four page textures once at boot (crisp, low VRAM — two canvas
  // uploads per page, no static PNGs). pageTex[i] ↔ PAGES[i].
  const pageTex = PAGES.map(buildPageTexture);

  // Cycle state. `activeIndex` is the chapter currently REVEALED on the stack
  // top (the one the UI card describes). The flipping sheet shows the PREVIOUS
  // chapter being turned away. Both advance by one each loop.
  let activeIndex = 0;
  const prevIndex = i => (i + PAGES.length - 1) % PAGES.length;

  // ---------- Paper grain bump map ----------
  // Procedural fine-grain noise so the matte legal bond catches a living,
  // non-plastic micro-texture under raking light. One shared tileable map for
  // every paper surface (flip front, flip back, revealed top sheet).
  const paperBump = (() => {
    const N = 512;
    const cv = document.createElement('canvas');
    cv.width = cv.height = N;
    const cx = cv.getContext('2d');
    const img = cx.createImageData(N, N);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 128 + (Math.random() - 0.5) * 64;     // fine fibrous speckle
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    cx.putImageData(img, 0, 0);
    cx.globalAlpha = 0.04;                              // faint long fibres → directional tooth
    cx.strokeStyle = '#000';
    for (let k = 0; k < 110; k++) {
      const y = Math.random() * N;
      cx.beginPath();
      cx.moveTo(0, y);
      cx.lineTo(N, y + (Math.random() - 0.5) * 9);
      cx.stroke();
    }
    const tex = new THREE.CanvasTexture(cv);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(3, 4);
    return tex;
  })();
  const PAPER_BACK_HEX = 0xF1ECDF;   // blank off-white reverse-side bond

  // ---------- Pile of static papers ----------
  // 25 extruded boxes — each with real thickness (PAGE_THICK). Microscopic
  // jitter on X/Z plus a slight yaw makes the stack edge read as a real
  // hand-stacked pile, not a laser-cut cube. Every 3rd page is 2% darker
  // so the plies "pop" against each other under the rim light.
  const pileGroup = new THREE.Group();
  world.add(pileGroup);
  const pileTopY = STACK_COUNT * STACK_GAP;

  // Shared ply geometry — cheaper than 25 distinct geometries.
  const plyGeo = new THREE.BoxGeometry(PAGE_W, PAGE_THICK, PAGE_L);

  // Two slightly-different paper tones; every 3rd ply uses the darker one.
  const paperLight = new THREE.Color(0xEAECEF);
  const paperDark  = paperLight.clone().multiplyScalar(0.98);   // ~2% darker

  for (let i = 0; i < STACK_COUNT; i++) {
    const m = new THREE.MeshStandardMaterial({
      color: (i % 3 === 0) ? paperDark : paperLight,
      roughness: 0.97,        // matte legal bond, not smooth plastic
      metalness: 0.04,
    });
    const ply = new THREE.Mesh(plyGeo, m);
    ply.receiveShadow = true;
    // The topmost few plies also cast, so the upper ply edges self-define.
    ply.castShadow = (i >= STACK_COUNT - 3);
    // Microscopic offsets — visible only at the ply edges.
    ply.position.set(
      (Math.random() - 0.5) * 0.06,
      i * STACK_GAP,
      (Math.random() - 0.5) * 0.07
    );
    ply.rotation.y = (Math.random() - 0.5) * 0.006;
    pileGroup.add(ply);
  }

  // ---------- Revealed page ----------
  const revealedGeo = new THREE.PlaneGeometry(PAGE_W, PAGE_L, 1, 1);
  const revealedMat = new THREE.MeshPhysicalMaterial({
    map: pageTex[0].texture,
    roughness: 0.88,           // matte legal bond
    metalness: 0.0,
    clearcoat: 0.05,
    clearcoatRoughness: 0.85,
    sheen: 0.22,
    sheenColor: new THREE.Color(0xfff3e2),
    sheenRoughness: 0.9,
    bumpMap: paperBump,
    bumpScale: 0.016,
    // Emissive ink — only the red highlight self-illuminates (map is black
    // elsewhere). Subtle on the well-lit resting page.
    emissive: new THREE.Color(0xffffff),
    emissiveMap: pageTex[0].emissiveMap,
    emissiveIntensity: 0.45,
    side: THREE.DoubleSide
  });
  const revealedPage = new THREE.Mesh(revealedGeo, revealedMat);
  revealedPage.rotation.x = -Math.PI / 2;
  revealedPage.position.y = pileTopY + 0.01;
  revealedPage.receiveShadow = true;
  world.add(revealedPage);

  // ---------- Flipping page (highly-subdivided, vertex-deformable) ----------
  // 64×64 segments — dense enough that the cylindrical curl reads as a
  // continuous arc with no faceting along the bend axis at any flip angle.
  // STAPLE-ORIGIN GEOMETRY (INSET pivot, done mathematically):
  // PlaneGeometry is created centered. We translate the BufferGeometry so the
  // page's STAPLE MARK — inset (STAPLE_INSET_X, STAPLE_INSET_Z) from the
  // top-left corner — becomes the strict local origin (0,0,0). A real staple
  // is inset from the edges, so hinging here looks natural. Consequence: a
  // small page tip BEHIND the staple now lives on the far side of the fold
  // axis (s < 0) and would "seesaw" down during the turn — handled by the
  // clamp in the curl (no curl past the axis) + the anti-seesaw lift below.
  // restPositions is captured AFTER the translate so the curl baseline matches.
  const SEG_X = 64, SEG_Z = 64;
  const flipGeo = new THREE.PlaneGeometry(PAGE_W, PAGE_L, SEG_X, SEG_Z);
  flipGeo.translate(PAGE_W / 2 - STAPLE_INSET_X, -PAGE_L / 2 + STAPLE_INSET_Z, 0);   // INSET staple → (0,0,0)
  const restPositions = flipGeo.attributes.position.array.slice();

  // FRONT/BACK as TWO meshes sharing ONE deforming geometry. The CPU curl
  // rewrites flipGeo every frame, so BOTH meshes deform identically — no copy,
  // no custom shader. The FRONT shows the contract texture on the FrontSide
  // only; the BACK shows blank off-white bond on the BackSide only. Because
  // each mesh renders a single face orientation, the reverse side never shows
  // mirrored/backwards text (the old DoubleSide bug) and the two coincident
  // faces never z-fight (only one orientation faces the camera per pixel).
  const flipFrontMat = new THREE.MeshPhysicalMaterial({
    map: pageTex[prevIndex(0)].texture,
    roughness: 0.86,           // thick matte legal bond
    metalness: 0.0,
    clearcoat: 0.06,           // whisper of coating → a soft specular that travels across the arc
    clearcoatRoughness: 0.85,
    sheen: 0.25,               // heavy-paper sheen at grazing angles
    sheenColor: new THREE.Color(0xfff3e2),
    sheenRoughness: 0.9,
    bumpMap: paperBump,
    bumpScale: 0.018,
    // Emissive ink — stronger here so the flagged clause keeps its red glow
    // even as the turning sheet rotates into deep shadow.
    emissive: new THREE.Color(0xffffff),
    emissiveMap: pageTex[prevIndex(0)].emissiveMap,
    emissiveIntensity: 0.8,
    side: THREE.FrontSide,
    transparent: true,
    vertexColors: true         // crease-AO via vertex colour (see applyFlip)
  });
  flipFrontMat.shadowSide = THREE.DoubleSide;   // robust cast shadow regardless of facing

  const flipBackMat = new THREE.MeshPhysicalMaterial({
    color: PAPER_BACK_HEX,     // blank off-white reverse — NO text map
    roughness: 0.9,
    metalness: 0.0,
    sheen: 0.2,
    sheenColor: new THREE.Color(0xfff3e2),
    sheenRoughness: 0.9,
    bumpMap: paperBump,
    bumpScale: 0.018,
    side: THREE.BackSide,
    transparent: true,
    vertexColors: true
  });
  flipBackMat.polygonOffset = true;             // nudge behind — belt-and-suspenders vs coincident flicker
  flipBackMat.polygonOffsetFactor = 1;
  flipBackMat.polygonOffsetUnits = 1;

  // Per-vertex color attribute — multiplies the diffuse map, so we use it
  // to bake a localized AO darkening near the staple pinch (see applyFlip).
  // Default to white; applyFlip overwrites each frame the curl is active.
  const colorAttr = new Float32Array(((SEG_X + 1) * (SEG_Z + 1)) * 3);
  for (let i = 0; i < colorAttr.length; i++) colorAttr[i] = 1;
  flipGeo.setAttribute('color', new THREE.BufferAttribute(colorAttr, 3));
  const flipPage     = new THREE.Mesh(flipGeo, flipFrontMat);  // FRONT (contract text)
  const flipPageBack = new THREE.Mesh(flipGeo, flipBackMat);   // BACK (blank bond)
  flipPage.castShadow     = true;    // the rearing page throws the dramatic shadow
  flipPageBack.castShadow = false;   // front already casts; avoid double

  // Pivot hierarchy — STRICTLY DECOUPLED to avoid the 360° "rubber band":
  //
  //   world
  //     └ flipTranslate  (OUTER group) — owns POSITION only.
  //       └ flipRotate   (INNER group) — owns ROTATION only (quaternion
  //                                       around FOLD_AXIS through the
  //                                       staple, which is this group's
  //                                       local origin).
  //         └ flipPage    (MESH) — owns the constant −π/2 X-orientation
  //                                  that lays the plane flat, the offset
  //                                  that places the TL corner at the
  //                                  origin, AND the per-vertex curl.
  //
  // The bounce on the previous single-group design came from translating
  // and rotating the same Object3D: as the rotation passed π the local
  // axes flipped sign, and the translation we were trying to apply "in
  // pivot-local space" effectively reversed direction. Now position runs
  // in the OUTER group's untransformed local space — strictly the world
  // — and the inner group is free to spin all the way around without
  // dragging the translation with it.
  const flipTranslate = new THREE.Group();   // outer: translation only
  world.add(flipTranslate);
  // Pivot at the INSET STAPLE (= flip hinge), seated on the stack top. Because
  // the geometry's origin IS the staple mark (see flipGeo.translate above),
  // rotating the inner group hinges exactly at the staple. This is the staple
  // location in `world` space — identical to the staple ASSET coords below.
  flipTranslate.position.set(-PAGE_W / 2 + STAPLE_INSET_X, pileTopY + 0.018, -PAGE_L / 2 + STAPLE_INSET_Z);

  const flipRotate = new THREE.Group();      // inner: rotation only
  flipTranslate.add(flipRotate);

  flipPage.rotation.x = -Math.PI / 2;
  // No positional offset: the geometry origin is the corner, and a corner at
  // the rotation pivot stays fixed under this −π/2 tilt (the origin is the one
  // invariant point of any rotation), so the corner coincides with flipRotate's
  // origin exactly. The page lays flat spanning the stack footprint. The back
  // mesh shares the identical transform so the two stay perfectly registered.
  flipPage.position.set(0, 0, 0);
  flipPageBack.rotation.x = -Math.PI / 2;
  flipPageBack.position.set(0, 0, 0);
  flipRotate.add(flipPage, flipPageBack);

  // ---------- Drop shadow plane (fake projected shadow under the flip) -----
  // Soft radial gradient anchored toward the staple corner of the texture,
  // fading out along the diagonal toward the free corner — mirrors how the
  // bent sheet's silhouette casts under the key light (9,14,6). Lies just
  // above the revealed top page (which is at pileTopY + 0.01) so it draws
  // over the static stack without z-fighting.
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = shadowCanvas.height = 256;
  {
    const sctx = shadowCanvas.getContext('2d');
    sctx.clearRect(0, 0, 256, 256);
    // Center the dark mass nearer the TL of the texture (which maps to the
    // staple side of the page footprint). Inner radius small → a soft but
    // distinct contact-shadow core. Deepened + widened for the macro shot:
    // because the rearing page now lifts mostly OFF-SCREEN, this projected
    // shadow is the primary cue that a massive sheet is looming overhead, so
    // it reads almost black at the core and carries a long, soft penumbra.
    const g = sctx.createRadialGradient(95, 85, 6, 112, 102, 178);
    g.addColorStop(0.00, 'rgba(0,0,0,0.94)');
    g.addColorStop(0.22, 'rgba(0,0,0,0.78)');
    g.addColorStop(0.48, 'rgba(0,0,0,0.46)');
    g.addColorStop(0.74, 'rgba(0,0,0,0.18)');
    g.addColorStop(1.00, 'rgba(0,0,0,0.00)');
    sctx.fillStyle = g;
    sctx.fillRect(0, 0, 256, 256);
  }
  const shadowTex = new THREE.CanvasTexture(shadowCanvas);
  shadowTex.colorSpace = THREE.SRGBColorSpace;
  const shadowMat = new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    depthWrite: false,
    opacity: 0,
  });
  const shadowPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(PAGE_W * 1.55, PAGE_L * 1.55),
    shadowMat
  );
  shadowPlane.rotation.x = -Math.PI / 2;
  // Centered over the page footprint, hovering just above the revealed top.
  shadowPlane.position.set(0, pileTopY + 0.013, 0);
  shadowPlane.renderOrder = 1;   // draw after the opaque pile
  world.add(shadowPlane);

  // ---------- Industrial staple / binding — top-left of the stack ----------
  // Dark gunmetal: high metalness, low roughness so the rim and key lights
  // both catch on it and read as something heavier than the paper.
  const stapleMat = new THREE.MeshStandardMaterial({
    color: 0x1f2024,
    metalness: 0.92,
    roughness: 0.28,
  });

  const stapleGroup = new THREE.Group();
  world.add(stapleGroup);

  // Anchor at the inset staple mark (shares STAPLE_INSET_* with the flip pivot).
  const stapleX = -PAGE_W / 2 + STAPLE_INSET_X;
  const stapleZ = -PAGE_L / 2 + STAPLE_INSET_Z;
  const stapleTop = pileTopY + 0.05;

  // Crown bar — flat across the top of the stack. Scaled DOWN and pulled toward
  // the corner so it no longer overhangs the curl zone (was 1.05×0.10×0.22).
  const crown = new THREE.Mesh(
    new THREE.BoxGeometry(0.82, 0.085, 0.20),
    stapleMat
  );
  crown.position.set(stapleX, stapleTop, stapleZ);
  // Subtle rotation so it doesn't feel laser-aligned to the page.
  crown.rotation.y = 0.08;
  crown.castShadow = true;
  stapleGroup.add(crown);

  // Two prongs descending into the pile (one each side of the crown).
  const prongDepth = STACK_COUNT * STACK_GAP * 0.85;
  for (const dx of [-0.33, 0.33]) {
    const prong = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, prongDepth, 0.20),
      stapleMat
    );
    // Position so the prong sits below the crown and disappears into the pile.
    const px = stapleX + Math.cos(crown.rotation.y) * dx;
    const pz = stapleZ - Math.sin(crown.rotation.y) * dx;
    prong.position.set(px, stapleTop - prongDepth / 2 - 0.04, pz);
    prong.rotation.y = crown.rotation.y;
    prong.castShadow = true;
    stapleGroup.add(prong);
  }

  // Tiny inner edge bevel on the crown — a darker shadow line catches the rim light.
  const bevel = new THREE.Mesh(
    new THREE.BoxGeometry(0.82, 0.012, 0.20),
    new THREE.MeshStandardMaterial({ color: 0x0a0b0d, metalness: 0.6, roughness: 0.45 })
  );
  bevel.position.set(stapleX, stapleTop - 0.055, stapleZ);
  bevel.rotation.y = crown.rotation.y;
  stapleGroup.add(bevel);

  // ---------- Shadow-casting KEY light (premium desk-lamp) ----------
  // Parented to `world` so it tracks the dossier and its shadow camera frames
  // the pile in local space (the rest of the rig points at the scene origin,
  // which the stack is translated far from). Premium warm off-white, strong,
  // raked from above the staple side so the rearing flip-page throws a long
  // hard shadow across the document.
  const shadowKey = new THREE.DirectionalLight(0xfff6ec, 2.05);
  shadowKey.position.set(-3.5, 17, -7.5);     // local: high, staple side
  shadowKey.castShadow = true;
  shadowKey.target.position.set(1.0, pileTopY, 0.5);
  world.add(shadowKey);
  world.add(shadowKey.target);

  // Crisp, high-resolution shadows.
  shadowKey.shadow.mapSize.set(2048, 2048);
  shadowKey.shadow.radius = 1.1;              // tight PCF kernel → hard edges
  shadowKey.shadow.bias = -0.00035;
  shadowKey.shadow.normalBias = 0.02;
  {
    const sc = shadowKey.shadow.camera;        // orthographic frustum over the pile + flip arc
    sc.near = 0.5;
    sc.far = 70;
    sc.left = -14; sc.right = 14;
    sc.top = 16;  sc.bottom = -16;
    sc.updateProjectionMatrix();
  }

  // ---------- Back-face FILL light ----------
  // When the flipping page stands vertical / rears over, its BACK face turns
  // away from the key and goes flat-gray. This fill sits BEHIND and to the LEFT
  // of the dossier, low and aimed UP at the back of the page mid-flight, so the
  // off-white reverse keeps a soft luminous paper mood through the whole arc.
  // Parented to `world` so it tracks the dossier. No shadow (fill only).
  const backFill = new THREE.DirectionalLight(0xf4ecdb, 0.85);
  backFill.position.set(-7, 4.5, 9.5);          // local: behind-left, low
  backFill.target.position.set(0.5, 6.0, 0);    // aim up into the reared page
  world.add(backFill);
  world.add(backFill.target);


  const dotMat = new THREE.MeshBasicMaterial({ color: ACCENT_VERM, transparent: true });
  const dotGeo = new THREE.SphereGeometry(0.085, 24, 24);
  const dot = new THREE.Mesh(dotGeo, dotMat);
  dot.visible = false;
  world.add(dot);
  // Sharp 1px ring around the dot — not a pulse; a stable target reticle.
  const dotHalo = new THREE.Mesh(
    new THREE.RingGeometry(0.18, 0.195, 64),
    new THREE.MeshBasicMaterial({ color: ACCENT_VERM, side: THREE.DoubleSide, transparent: true, opacity: 0.95 })
  );
  dotHalo.rotation.x = -Math.PI / 2;
  dotHalo.visible = false;
  world.add(dotHalo);

  // ---------- Target word world position (cached) ----------
  const targetWorld = new THREE.Vector3();
  function setTargetFromPage(i) {
    const tgt = pageTex[i].target;
    if (tgt) {
      targetWorld.x = tgt.local.x;
      targetWorld.y = pileTopY + 0.03;
      targetWorld.z = tgt.local.z;
    } else {
      targetWorld.set(0, pileTopY + 0.03, 0);
    }
  }
  setTargetFromPage(0);

  // ---------- Page-flip animation (flip & tuck, diagonal conical curl) -------
  // progress ∈ [0,1] over FLIP_DUR (~2.4s). Two phases:
  //
  //   PHASE 1  LIFT  (p: 0 → 0.55)
  //     The page rises around its top-left staple, bending conically as the
  //     bottom-right corner is pulled up & over. easeInOutCubic on rotation
  //     (not the previous easeOutQuint) so the bend has time to read against
  //     the rotation — without this, the page slams to its end pose in the
  //     first ~13% of the timeline and the rest is settle, which is exactly
  //     what made the original feel like a flipping board.
  //
  //   PHASE 2  TUCK  (p: 0.55 → 1.0)
  //     Rotation HOLDS at its phase-1 apex (~115°). The pivot descends in
  //     −Y straight through the pile and shifts slightly in +Z so the sheet
  //     slides behind the stack. Opacity is driven by descent (1−tuckEase),
  //     so the sheet dissolves into the shadow of the stack rather than
  //     fading on a separate clock.
  //
  // CONICAL CURL (apex at the staple)
  //   Each vertex is projected into a (s, d) frame where:
  //     • s = signed distance along the diagonal, 0 at staple → D at BR,
  //     • d = signed distance along the anti-diagonal (the fold-line dir.).
  //   Bending happens in s: θ(s) = θ_max · (s/D)^γ with γ < 1 so the bend
  //   ANGLE accumulates faster near the staple → tighter radius near the
  //   anchor, gentler at the free corner (a true cone apex behaviour).
  //   The bent (s,0) flat point projects to (R·sinθ, R·(1−cosθ)) on the arc,
  //   with R = s/θ — small near s=0 (tight curl) growing with s (loose curl).
  //   The curl envelope stays elevated during PHASE 2 — real paper doesn't
  //   un-curl while it's being held in a flipped pose.
  //
  // ANCHOR PIN
  //   A smoothstep on radial distance from the staple keeps vertices inside
  //   ~1 inch of the corner with near-zero displacement and zero lift, so
  //   the staple region doesn't shear off the cone apex.
  //
  // GRAVITY DROOP
  //   A small downward bias on lift, scaled by (s/D)^1.6 and an envelope
  //   that peaks mid-flip, makes the free corner sag — paper, not cardboard.
  const easeOutQuint   = t => 1 - Math.pow(1 - t, 5);
  // PRIMARY lift/tuck easing. easeInOutQuint has a much flatter start than
  // easeInOutCubic (derivative at 0 is 0 with a long ramp-up before the
  // mid-flight acceleration), which kills the "abrupt start" complaint.
  // The end is also softer — reads as the page settling rather than slamming.
  const easeInOutQuint = t => t < 0.5
    ? 16 * t * t * t * t * t
    : 1 - Math.pow(-2 * t + 2, 5) / 2;

  // Rest position of the OUTER translation group — cached so we can drive
  // the descent relative to a stable origin without accumulating drift.
  const PIVOT_REST_X = flipTranslate.position.x;
  const PIVOT_REST_Y = flipTranslate.position.y;
  const PIVOT_REST_Z = flipTranslate.position.z;

  // Single-timeline keyframes for the FREE-HANG metaphor:
  // "Flip the page over the top with your right hand, then LET GO. The
  //  page drops and hangs freely behind the stack at a 270° angle."
  //
  //   ROT_FULL       — ~300°. The page rears up and over, then continues past
  //                    the vertical hang so it sweeps DOWN and BEHIND the
  //                    stack — "tucking" under the dossier rather than hanging
  //                    in the void. Combined with the late descent below.
  //   TUCK_BACK_Z    — +Z back-shift so the tucking sheet slides BEHIND the
  //                    rear face of the pile.
  //   TUCK_DROP_Y    — −Y descent in the LATE phase so the page sinks under
  //                    the stack's plane and is occluded before it fades.
  const ROT_FULL      = Math.PI * (315 / 180);   // 315° — page rears up and over, then the tight binding U-turn curls the body back to lie FLAT UNDER the stack (occluded), not draping into the void
  const TUCK_BACK_Z   = 0.55;
  const TUCK_DROP_Y   = 0.45;
  const TUCK_RIGHT_X  = 0.0;

  // Apex split for the two-segment angle curve. At p=P_APEX the page has
  // rotated EXACTLY 180° and the gravity-takeover phase begins.
  const P_APEX        = 0.55;

  // Opacity is ANGLE-locked at 240° → 270° (the freefall window).
  // Independent of the easing curve — always begins when the page is
  // physically in the last 30° of its arc, fully gone at the hang.
  const FADE_ANGLE_START = 240 * Math.PI / 180;
  const FADE_ANGLE_END   = 270 * Math.PI / 180;
  const FADE_ANGLE_SPAN  = FADE_ANGLE_END - FADE_ANGLE_START;

  // ---- ORGANIC 4-PHASE easing — C∞ by construction (so C2 is guaranteed) ----
  // A real hand-pulled page turn is NOT symmetric (sine.inOut read as a robotic
  // wiper). Instead of easing the POSITION with stitched formulas, we define a
  // smooth, strictly-POSITIVE angular-VELOCITY profile and INTEGRATE it. The
  // position is the normalised cumulative integral, so:
  //   • velocity = the curve we draw  → we control the 4 phases directly,
  //   • acceleration = its derivative → continuous & spike-free (sum of
  //     Gaussians is infinitely differentiable: no jerk, no whip, no cliff),
  //   • velocity is FLOOR + (positive humps) > 0 everywhere → never stalls.
  //
  //   v(t) = FLOOR
  //        + A1·exp(−((t−C1)/W1)²)   ← Phase-1 "hand pull" hump (early, modest)
  //        + A2·exp(−((t−C2)/W2)²)   ← Phase-3 "gravity drop" hump (late, TALLEST)
  //
  //   Phase 1  (0.00–0.30)  hand pull : v rises to the C1 peak, then decays
  //   Phase 2  (0.30–0.45)  hang time : v sinks to a positive local MIN (the
  //                                     page feels weightless but never stops)
  //   Phase 3  (0.45–0.80)  gravity   : C2 hump — the highest velocity of the turn
  //   Phase 4  (0.80–1.00)  air cushion: v decays smoothly back to FLOOR → a long,
  //                                     soft deceleration that settles into rest
  // Built ANALYTICALLY: the integral of a Gaussian is the error function (erf),
  // which is C∞, so the easing has provably smooth velocity AND acceleration
  // (no LUT stepping, no piecewise seams anywhere).
  //   ∫₀ᵖ exp(−((t−C)/W)²) dt = (W√π/2)·[erf((p−C)/W) − erf(−C/W)]
  //   pos(p) = [FLOOR·p + A1·G1(p) + A2·G2(p)] / pos_denominator   (→ 0..1)
  const _flipEase = (() => {
    const FLOOR = 0.24;
    const A1 = 0.40, C1 = 0.12, W1 = 0.132;   // hand pull (early, modest)
    const A2 = 1.80, C2 = 0.62, W2 = 0.128;   // gravity drop — sharper SNAP: taller peak, shifted slightly earlier so the air-cushion tail (0.62→1.0) is longer & breathes out slower
    // erf — Abramowitz-Stegun 7.1.26 (max abs error 1.5e-7), smooth in x.
    const erf = x => {
      const s = x < 0 ? -1 : 1;
      const ax = Math.abs(x);
      const t = 1 / (1 + 0.3275911 * ax);
      const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-ax * ax);
      return s * y;
    };
    const HALF_RT_PI = Math.sqrt(Math.PI) / 2;
    const gint = (p, C, W) => W * HALF_RT_PI * (erf((p - C) / W) - erf(-C / W));
    const numer = p => FLOOR * p + A1 * gint(p, C1, W1) + A2 * gint(p, C2, W2);
    const denom = numer(1);
    return p => numer(clamp01(p)) / denom;
  })();

  function angleOfP(p) {
    const rotFull = (window.__rotFull !== undefined ? window.__rotFull : 315) * Math.PI / 180;
    return rotFull * _flipEase(p);
  }

  // -- Pre-compute per-vertex constants (run once at boot) --
  // Diagonal-frame basis vectors in (ux, uy) space, where
  //   ux = x_geom + PAGE_W/2   (0 at staple side, +W at right edge)
  //   uy = PAGE_L/2 − y_geom    (0 at staple side, +L at bottom edge)
  const DIAG_LEN = Math.hypot(PAGE_W, PAGE_L);
  const N_X      =  PAGE_W / DIAG_LEN;   // diagonal direction (ux comp)
  const N_Y      =  PAGE_L / DIAG_LEN;   // diagonal direction (uy comp)
  const P_X      = -PAGE_L / DIAG_LEN;   // anti-diagonal direction (ux comp)
  const P_Y      =  PAGE_W / DIAG_LEN;   // anti-diagonal direction (uy comp)
  // Rotation axis: the anti-diagonal direction projected into pivot-local
  // XZ (the page-plane in pivot space). Same components as P_X / P_Y because
  // geometry +Y maps to pivot +Z under flipPage's −π/2 X-rotation.
  const FOLD_AXIS = new THREE.Vector3(P_X, 0, P_Y);

  // Diagonal CREASE axis (staple → free corner) for the subtle fold roll, and
  // scratch quaternions reused each frame (no per-frame allocation).
  const CREASE_AXIS = new THREE.Vector3(N_X, 0, N_Y).normalize();
  const _qFold   = new THREE.Quaternion();
  const _qCrease = new THREE.Quaternion();

  // Per-vertex caches: distance along diagonal (s), along anti-diagonal (d),
  // and an anchor-pin weight in [0,1] (0 = pinned to staple, 1 = fully free).
  const N_VERTS = restPositions.length / 3;
  const vS   = new Float32Array(N_VERTS);
  const vD   = new Float32Array(N_VERTS);
  const vPin = new Float32Array(N_VERTS);
  {
    // Staple pin: the page is physically pierced/bound here, so a generous
    // RIGID DISC around the staple stays perfectly flat at Z=0 and never
    // participates in the curl — this is what stops the paper bending THROUGH
    // the staple crown. Inside r < PIN_INNER we lock fully; PIN_INNER→PIN_OUTER
    // smoothsteps up to full freedom. Widened (was 0.55/1.85) so the flat disc
    // is comfortably larger than the (now smaller) staple footprint.
    const PIN_INNER = 0.95;
    const PIN_OUTER = 2.40;
    for (let i = 0, vi = 0; i < restPositions.length; i += 3, vi++) {
      const ux = restPositions[i];          // staple corner now at x = 0
      const uy = -restPositions[i + 1];      // staple corner now at y = 0
      vS[vi] = ux * N_X + uy * N_Y;     // ∈ [0, DIAG_LEN]
      vD[vi] = ux * P_X + uy * P_Y;     // ∈ [−PAGE_W·PAGE_L/D, +PAGE_W·PAGE_L/D]
      const r  = Math.hypot(ux, uy);
      const t  = clamp01((r - PIN_INNER) / (PIN_OUTER - PIN_INNER));
      vPin[vi] = t * t * (3 - 2 * t);   // smoothstep
    }
  }

  function applyFlip(progress) {
    const p = clamp01(progress);

    // ============================================================
    // SINGLE CONTINUOUS TIMELINE — FREE-HANG METAPHOR
    // ------------------------------------------------------------
    //   rotation   : 0 → 270°       piecewise C1: segment A pull (0→180°)
    //                                 with deliberate-swift accel,
    //                                 segment B drop (180→270°) decelerating
    //                                 into the hang. NO seam discontinuity.
    //   translation: rest → +Z      smoothstep to TUCK_BACK_Z, completes
    //                                 by p≈0.85 so the hang phase is on
    //                                 a stable Z.
    //   curl       : tight → drape  peaky tight curl during pull damps past
    //                                 the apex; a soft drape floor (12%) rises
    //                                 to take over. The sum is NEVER zero past
    //                                 the apex — the hanging page retains a
    //                                 natural wave.
    //   droop      : build → hold   stays elevated through the hang so the
    //                                 free corner sags downward.
    //   opacity    : 1.0 hold → fade ANGLE-locked: 1.0 until rotation ≥ 240°,
    //                                 reaches 0 at 270°.
    //   drop shadow: in → peak → out p-based envelope (page is BEHIND the
    //                                 stack past ~p=0.5 so the shadow has to go).
    //
    // Rotation is applied to flipRotate (inner group), translation to
    // flipTranslate (outer group). They never share an Object3D.
    // ============================================================

    // -- ROTATION on inner group ------------------------------------------
    // Custom two-segment curve — see angleOfP() for derivation.
    const baseAngle = angleOfP(p);
    // Diagonal CREASE ROLL: a stapled sheet folds along the diagonal, not a
    // pure axis. A subtle roll about the staple→corner diagonal builds as the
    // page pulls and releases by the apex — the crease tension at the staple.
    const creaseRoll = Math.sin(clamp01(p / P_APEX) * Math.PI) * 0.05;
    _qFold.setFromAxisAngle(FOLD_AXIS, baseAngle);
    _qCrease.setFromAxisAngle(CREASE_AXIS, creaseRoll);
    flipRotate.quaternion.copy(_qFold).multiply(_qCrease);

    // -- TRANSLATION on outer group: the LATE "tuck under" -----------------
    // No translation during the rear-up (the staple stays anchored). Then, in
    // the LATE phase (p ∈ [0.58, 1.0]), the whole sheet is pushed DOWN (−Y) and
    // BACK (+Z) on a Power2 ease-out so it slides beneath the stack's plane and
    // behind its rear face — tucking under the dossier. Decisive, no bounce.
    const tuckRaw  = clamp01((p - 0.58) / 0.42);
    const tuckEase = 1 - (1 - tuckRaw) * (1 - tuckRaw);   // Power2.easeOut
    const liftEnv  = Math.max(0, Math.sin(baseAngle));    // (drives shadow penumbra below)
    flipTranslate.position.set(
      PIVOT_REST_X,
      PIVOT_REST_Y - tuckEase * TUCK_DROP_Y,
      PIVOT_REST_Z + tuckEase * TUCK_BACK_Z
    );

    // -- DYNAMIC SHADOW PENUMBRA (hang = soft/diffuse → settle = tight contact) --
    // PCFSoftShadowMap kernel widens hard as the page rears overhead (a big,
    // diffuse penumbra during the weightless hang), then COLLAPSES to a tight,
    // dark contact shadow strictly during the final air-cushion settle — the
    // real occluder-distance ↔ penumbra relationship, exaggerated for drama.
    //   • liftEnv (sin of the turn angle) drives the SOFT widening at the apex.
    //   • settleTight (the tuck ease) clamps the kernel DOWN to a crisp contact
    //     edge as the sheet meets the stack — so the shadow "snaps" sharp on land.
    if (shadowKey.shadow) {
      const settleTight = tuckEase;                       // 0 → 1 across p∈[0.58,1]
      const soft = 1.0 + liftEnv * 9.0;                   // diffuse during the overhead hang
      shadowKey.shadow.radius = Math.max(0.5, soft * (1 - 0.62 * settleTight));
    }

    // -- TRAVELLING CREASE SPECULAR (fast gravity drop) --
    // During the snap (velocity peak ≈ p0.62) the taut, fast-moving sheet
    // catches a sharper glint along the fold. Tighten the clearcoat lobe only
    // through the drop window, then relax — a specular highlight that travels
    // across the crease exactly when the page cuts through the air the hardest.
    const gravDrop = Math.exp(-(((p - 0.62) / 0.13) ** 2));   // 0..1, peaks at the drop
    flipFrontMat.clearcoat = 0.06 + gravDrop * 0.20;
    flipFrontMat.clearcoatRoughness = 0.85 - gravDrop * 0.42; // tighter lobe → crisper glint
    flipFrontMat.sheen = 0.25 + gravDrop * 0.18;

    // -- OPACITY: held FULLY SOLID until the page has physically slid under
    // the stack — occlusion does the hiding, not a fade. Only a whisper of
    // fade across the final p ∈ [0.95, 1.0] cleans up any sliver still poking
    // past the stack footprint before the loop restarts.
    const fo = clamp01((p - 0.95) / 0.05);
    const opacity = 1 - fo * fo * (3 - 2 * fo);
    flipFrontMat.opacity = opacity;
    flipBackMat.opacity  = opacity;
    flipPage.visible     = opacity > 0.001;
    flipPageBack.visible = opacity > 0.001;

    // -- DROP SHADOW under the lifting page.
    // Page is BELOW the stack once rotation passes ~180°, so the shadow
    // can't be cast on the pile top anymore. Envelope: ramps in over
    // 0–0.10, holds strong through the overhead lift, fades out 0.48–0.62.
    // PRONOUNCED for the macro shot — the rearing sheet leaves frame, so this
    // shadow is what tells the eye a massive page is hanging overhead: it
    // darkens hard, grows large, and SWEEPS across the stack toward the free
    // corner as the page climbs (a directional cue for the lift).
    const heightEnv = Math.sin(clamp01(p / 0.55) * Math.PI);
    const shFadeIn  = clamp01(p / 0.10);
    const shFadeOut = 1 - clamp01((p - 0.48) / 0.14);
    // Dialed back (was 0.92) now that a REAL cast shadow does the heavy
    // lifting — this fake plane is just a soft contact-AO floor under the lift.
    shadowMat.opacity = 0.42 * shFadeIn * shFadeOut * (0.72 + 0.40 * heightEnv);
    shadowPlane.position.x = heightEnv * 0.62;
    shadowPlane.position.z = heightEnv * 0.46;
    shadowPlane.scale.setScalar(1.0 + heightEnv * 0.55);

    // Early-out if the page is invisible — no point shading vertices we
    // won't see (but make sure the geometry update still flushes).
    if (opacity <= 0.001) {
      flipGeo.attributes.position.needsUpdate = true;
      return;
    }

    // -- CURL ENVELOPE — PEAK (phase A) + GRAVITY-RELAXED WAVE (phase B).
    // Two superposed components combined by max():
    //
    //   peakPart : sharp conical curl during the pull. PEAKS at p≈0.45
    //              (mid pull-phase), then DAMPS aggressively past the
    //              apex (window p ∈ [0.60, 0.80]) — "the hand releases
    //              the curled corner the moment the page is over the top."
    //              At p=0.85 the peak component is already 0; pure drape
    //              past that point.
    //
    //   restPart : gentle drape that ramps in across p ∈ [0.50, 0.70]
    //              and TAPERS through the snap (p ∈ [0.85, 1.0]) as
    //              gravity pulls the falling sheet mostly taut. Final
    //              hang amplitude is ~25% of the entry amplitude — a
    //              subtle wave along the bottom edge, not a frozen
    //              cylinder bend.
    //
    // Tuned so the residual max|z| at p=1.0 lands near 0.21 — visible
    // wave, not rigid plastic.
    // Mid-flight bow (the rear-up drama) — peaks near the apex, fades after.
    const peakRaw   = Math.sin(Math.pow(p, 0.85) * Math.PI);
    const peakDampR = 1 - clamp01((p - 0.55) / 0.35);
    const peakDamp  = peakDampR * peakDampR * (3 - 2 * peakDampR);
    const peakPart  = peakRaw * peakDamp;

    // ASYMMETRIC TUCK CURL — the crucial fix. The bend intensity does NOT
    // return to zero at the end. After the apex the curl RE-TIGHTENS into a
    // sustained, sharp U-turn at the binding (held at full strength at p=1),
    // so the body of the page wraps DOWN and UNDER the stack instead of
    // snapping flat into a rigid plank that slices into the void.
    const tuckRamp  = clamp01((p - 0.52) / 0.46);
    const tuckCurl  = tuckRamp * tuckRamp * (3 - 2 * tuckRamp);   // smoothstep, HOLDS 1 at the end (no decay)
    const tuckPart  = (window.__tuckAmp !== undefined ? window.__tuckAmp : 0.55) * tuckCurl;

    const curlEnvelope = Math.max(peakPart, tuckPart);
    const thetaMax = curlEnvelope * Math.PI * 0.92;

    // -- GRAVITY DROOP — builds and SUSTAINS through the hang (no taper).
    // The free corner stays drooped while the page is hanging — paper has
    // weight, the bottom of a hanging sheet sags toward the floor.
    const droopBuild = clamp01((p - 0.15) / 0.40);
    const droopEnv   = droopBuild * 0.75;

    const arr = flipGeo.attributes.position.array;
    const col = flipGeo.attributes.color.array;

    if (Math.abs(thetaMax) < 1e-4 && droopEnv < 1e-4) {
      // Flat — fast path, snap vertices back to rest and clear vertex AO.
      for (let i = 0; i < arr.length; i += 3) {
        arr[i]     = restPositions[i];
        arr[i + 1] = restPositions[i + 1];
        arr[i + 2] = 0;
        col[i]     = 1;
        col[i + 1] = 1;
        col[i + 2] = 1;
      }
    } else {
      // γ < 1 → bend angle ramps fastest near the anchor (cone apex). During
      // the tuck we DROP the exponent toward ~0.22 so the bend SATURATES right
      // at the binding (tight U-turn radius) while the body beyond the hinge
      // stays straight and flat — a true hairpin, not a cone.
      const SHAPE_EXP = 0.55 - 0.33 * tuckCurl;

      // -- BINDING-FLATTEN basis (true vertex deformation, NO rigid seesaw) --
      // flipRotate rigidly rotates the inner group by `baseAngle` about the
      // fold axis. For vertices BEHIND the binding we apply an equal-and-
      // opposite per-vertex rotation in geometry space so they end up exactly
      // on the stack plane (canceling the rigid turn) — the staple corner and
      // back tip stay perfectly FLAT and FLUSH while the body of the sheet
      // rears up. The flatten weight w travels like a fold line from the
      // binding outward: w=1 behind the binding (s≤0), smoothstepping to w=0
      // across the hinge zone (0 → S_HINGE) into the freely-lifting body.
      const cosA    = Math.cos(baseAngle);
      const sinA    = Math.sin(baseAngle);
      const S_HINGE = 1.70;

      // Crease-AO parameters — see vertex-color block below.
      // The pinch shadow peaks at s = AO_PEAK (just past the staple pin, where
      // the curl curvature is sharpest), with Gaussian width AO_SIGMA. Past
      // s > AO_PEAK + 2·AO_SIGMA the page reads as bright paper again.
      const AO_PEAK     = 1.7;
      const AO_SIGMA    = 1.55;
      const AO_STRENGTH = 0.55 * Math.min(1, curlEnvelope * 1.4);
      const INV_2SIG2   = 1 / (2 * AO_SIGMA * AO_SIGMA);
      const invDiag   = 1 / DIAG_LEN;

      for (let i = 0, vi = 0; i < arr.length; i += 3, vi++) {
        const s   = vS[vi];
        const d   = vD[vi];
        const pin = vPin[vi];
        const sN  = Math.max(0, s) * invDiag;             // s/D; back-tip (s<0) → 0 (no curl past the fold axis)

        // Bend angle accumulated from anchor to this vertex.
        const theta = thetaMax * Math.pow(sN, SHAPE_EXP);

        // Circular-arc projection of the flat (s,0) point. R = s/θ varies
        // with the vertex, giving the conical signature: tighter near the
        // apex (small s ⇒ small R) and loosening toward the free corner.
        let sNew, lift;
        if (Math.abs(theta) < 1e-4) {
          sNew = s;
          lift = 0;
        } else {
          const R = s / theta;
          sNew = R * Math.sin(theta);
          lift = R * (1 - Math.cos(theta));
        }

        // Anchor pin: blend toward the rest pose near the staple.
        sNew = s + (sNew - s) * pin;
        lift *= pin;

        // Gravity droop on the free corner — extra downward bias in
        // geometry-local +Z (the "up" side before the pivot rotates).
        // Weighted by sN^1.6 so it's strongest at the BR corner, and by
        // pin so the staple is unaffected. Bumped from 0.50 to 0.65 for a
        // more visible sag at the free tip.
        lift -= droopEnv * Math.pow(sN, 1.6) * 0.65 * pin;

        // -- BINDING FLATTEN: counter-rotate the back/staple region flat.
        // sFlat / liftFlat are the geometry coords that, AFTER the group's
        // rigid flipRotate(baseAngle), land the vertex back on the flat stack
        // plane (s·cos canceled in-plane, −s·sin out-of-plane). Blended in by
        // the travelling fold weight w — 1 behind the binding, 0 in the body.
        let w;
        if (s <= 0) {
          w = 1;
        } else {
          const tt = clamp01(s / S_HINGE);
          w = 1 - tt * tt * (3 - 2 * tt);
        }
        if (w > 1e-4) {
          sNew = sNew * (1 - w) + (s * cosA) * w;
          lift = lift * (1 - w) + (-s * sinA) * w;
        }

        // Rebuild geometry coords in the (s, d) basis.
        const newUx = sNew * N_X + d * P_X;
        const newUy = sNew * N_Y + d * P_Y;

        arr[i]     = newUx;                  // staple-origin frame (TL = 0,0)
        arr[i + 1] = -newUy;
        arr[i + 2] = lift;

        // -- Crease-AO via vertex color (multiplies the diffuse map).
        // Gaussian centered at s = AO_PEAK so the darkest band sits next
        // to the staple where the curl radius is tightest, NOT mid-page.
        // The apex of the curl (largest sN, largest lift) gets unchanged
        // white → catches the key light. Slight warm-dark tint (0.96, 0.92)
        // keeps the shadow reading as paper-shadow, not soot.
        const ds      = s - AO_PEAK;
        const aoGauss = Math.exp(-ds * ds * INV_2SIG2);
        const dark    = AO_STRENGTH * aoGauss;
        const c       = 1 - dark;
        col[i]     = c;
        col[i + 1] = c * 0.965;
        col[i + 2] = c * 0.925;
      }
    }
    flipGeo.attributes.position.needsUpdate = true;
    flipGeo.attributes.color.needsUpdate    = true;
    flipGeo.computeVertexNormals();
  }

  // Back-compat shim for window.__hero.applyCurl (was used by debug helpers).
  const applyCurl = applyFlip;

  // ---------- Project a world point to viewport pixel coords ----------
  // The dot is a child of `world`, so its position needs the world matrix applied
  // before projection (otherwise we'd project a pre-rotation point).
  let canvasRect = canvas.getBoundingClientRect();
  let spanAnchorRect = spanAnchor.getBoundingClientRect();
  const refreshRects = () => {
    canvasRect = canvas.getBoundingClientRect();
    spanAnchorRect = spanAnchor.getBoundingClientRect();
  };

  const _projV = new THREE.Vector3();
  function projectLocalToViewport(localVec) {
    _projV.copy(localVec);
    _projV.applyMatrix4(world.matrixWorld);
    _projV.project(camera);
    return {
      x: (_projV.x * 0.5 + 0.5) * canvasRect.width  + canvasRect.left,
      y: (-_projV.y * 0.5 + 0.5) * canvasRect.height + canvasRect.top
    };
  }

  // ---------- Trace-line state ----------
  // (No state needed — flicker is computed inline each frame from `t`.)

  // ---------- Animation timeline ----------
  // 0.00 – 2.50  : page flip with sin-based bend (FLIP_DUR)
  // 2.50 – 2.70  : dot snaps on (instant reveal + 1-frame ring kick)
  // 2.70 – 3.25  : red hairline shoots from dot to Phoenix Trace anchor
  // 3.25 – 3.45  : Phoenix Trace block flickers in (CRT)
  // 3.45 – 5.80  : held verdict
  // 5.80 – 6.50  : fade out & reset (loop)
  const T_FLIP_END = FLIP_DUR;          // 2.50
  const T_DOT      = T_FLIP_END;        // 2.50 — snap instantly at flip end
  const T_LINE     = T_FLIP_END + 0.20; // 2.70
  const T_BADGE    = T_FLIP_END + 0.30; // impact-triggered: card kicks in right as the page LANDS
  const T_FADE     = 5.80;
  const T_FADE_END = 6.50;

  // ---------- UI card + page-swap synchronisation ----------
  // The Phoenix-trace card mirrors the ACTIVE (revealed) chapter. Texture +
  // card swaps happen at the loop boundary, while the flat opaque flip sheet
  // covers the revealed page and the card is hidden — so the change is only
  // ever SEEN once the page has slammed down and the card flickers back in.
  const cardId     = spanAnchor.querySelector('.id');
  const cardClause = spanAnchor.querySelector('.clause');
  const cardTag    = spanAnchor.querySelector('.tag');
  const cardCi     = spanAnchor.querySelector('.ci');
  function updateCard(i) {
    const p = PAGES[i];
    if (cardId)     cardId.textContent     = p.spanId;
    if (cardClause) cardClause.textContent = p.clauseLabel;
    if (cardTag)    cardTag.textContent    = p.clauseTag;
    if (cardCi)     cardCi.textContent     = p.ci;
  }
  function setRevealed(i) {
    revealedMat.map         = pageTex[i].texture;
    revealedMat.emissiveMap = pageTex[i].emissiveMap;
    revealedMat.needsUpdate = true;
    setTargetFromPage(i);
  }
  function setFlip(i) {
    flipFrontMat.map         = pageTex[i].texture;
    flipFrontMat.emissiveMap = pageTex[i].emissiveMap;
    flipFrontMat.needsUpdate = true;
  }
  function advancePage() {
    activeIndex = (activeIndex + 1) % PAGES.length;
    setRevealed(activeIndex);          // newly revealed chapter (hidden under the flat sheet)
    setFlip(prevIndex(activeIndex));   // the sheet that turns away this loop
    updateCard(activeIndex);
  }
  updateCard(activeIndex);             // seed card for the first loop (chapter I)
  let __lastT = 0;

  function tick(now) {
    if (disposed) return; // a frame may already be queued when dispose() runs
    let t = (now / 1000) % LOOP;
    if (window.__freeze !== undefined) t = window.__freeze;
    // Reduced-motion: pin the loop clock to a resolved frame (after the recompute
    // above so it is not clobbered). The reschedule below is gated on !reduced, so
    // tick paints exactly one static frame: flipped page + trace line + verdict card.
    if (reduced) t = REDUCED_T;

    // Loop-boundary detection → advance to the next chapter. The swap happens
    // while the flip sheet is flat/opaque and the card hidden, never mid-motion.
    if (t < __lastT) advancePage();
    __lastT = t;

    // -------- Page flip (0 → FLIP_DUR) --------
    const flipping = t < T_FLIP_END;
    const flipP = clamp01(t / FLIP_DUR);
    applyFlip(flipP);

    // Page visibility is owned by applyFlip() now — opacity ties to the
    // tuck-descent so the sheet dissolves into the shadow of the stack as
    // it slides under, instead of fading on a separate post-flip clock.
    // After T_FLIP_END the sheet stays hidden (applyFlip(1) leaves
    // opacity ≈ 0); it pops back at t≈0 when applyFlip(0) runs.

    // Telemetry-overlay fade (dot + line + badge) at the END of the cycle.
    const verdictOut = clamp01((t - T_FADE) / (T_FADE_END - T_FADE));

    // -------- Dot — hidden during flip; instant snap at T_DOT --------
    if (!flipping && t < T_FADE_END) {
      dot.visible     = true;
      dotHalo.visible = true;
      dot.position.copy(targetWorld);
      dotHalo.position.copy(targetWorld);

      // Tiny ring kick: a 200ms expansion right at the snap, then settles to 1.
      const kick = clamp01((t - T_DOT) / 0.20);
      const ringScale = 1 + (1 - easeOutExpo(kick)) * 1.6;
      dotHalo.scale.setScalar(ringScale);
      dotHalo.material.opacity = (0.85 + (1 - kick) * 0.15) * (1 - verdictOut);

      dot.scale.setScalar(1);
      dot.material.opacity = 1 - verdictOut;
    } else {
      dot.visible     = false;
      dotHalo.visible = false;
    }

    // -------- Hairline: dot → Phoenix Trace anchor --------
    const lineT = clamp01((t - T_LINE) / 0.55);
    if (lineT > 0 && t < T_FADE_END) {
      const dotPx = projectLocalToViewport(targetWorld);
      const targetEndX = spanAnchorRect.left;
      const targetEndY = spanAnchorRect.top;

      const eased = easeOutCubic(lineT);
      const endX = dotPx.x + (targetEndX - dotPx.x) * eased;
      const endY = dotPx.y + (targetEndY - dotPx.y) * eased;

      svgLine.setAttribute('x1', dotPx.x.toFixed(1));
      svgLine.setAttribute('y1', dotPx.y.toFixed(1));
      svgLine.setAttribute('x2', endX.toFixed(1));
      svgLine.setAttribute('y2', endY.toFixed(1));
      svgLine.style.opacity = (1 - verdictOut).toFixed(2);
    } else {
      svgLine.style.opacity = 0;
    }

    // -------- Phoenix Trace block: HARD-GATED on page-turn completion --------
    // STRICT rule: the card may not begin its reveal until the flip has reached
    // progress === 1.0 (the page fully tucked and stationary). It is gated on
    // BOTH `!flipping` (flipP has hit 1.0 at t === T_FLIP_END) AND `t >= T_BADGE`
    // (a short post-landing "impact" beat). Because T_BADGE > T_FLIP_END, the
    // card can NEVER fade in while the sheet is still in motion.
    const flipDone = !flipping;                 // flipP === 1.0
    if (!flipDone || t < T_BADGE) {
      spanAnchor.style.opacity = 0;
    } else if (t < T_FADE_END) {
      const lt = t - T_BADGE;
      let flick = 1;
      if      (lt < 0.04) flick = 0;
      else if (lt < 0.06) flick = 1;
      else if (lt < 0.08) flick = 0;
      else if (lt < 0.12) flick = 1;
      else if (lt < 0.15) flick = 0.35;
      else                flick = 1;
      spanAnchor.style.opacity = (flick * (1 - verdictOut)).toFixed(2);
    } else {
      spanAnchor.style.opacity = 0;
    }

    // -------- Camera breathing on the ortho rig (mild parallax) --------
    if (window.__pose) {
      const p = window.__pose;
      if (p.world) {
        if (p.world.rx !== undefined) world.rotation.x = p.world.rx;
        if (p.world.ry !== undefined) world.rotation.y = p.world.ry;
        if (p.world.rz !== undefined) world.rotation.z = p.world.rz;
        if (p.world.x !== undefined) world.position.x = p.world.x;
        if (p.world.y !== undefined) world.position.y = p.world.y;
        if (p.world.z !== undefined) world.position.z = p.world.z;
      }
      if (p.fov) {
        const a = cw() / ch();
        if (!window.__dbgCam) window.__dbgCam = new THREE.PerspectiveCamera(p.fov, a, 0.1, 1000);
        window.__dbgCam.fov = p.fov; window.__dbgCam.aspect = a; window.__dbgCam.updateProjectionMatrix();
        camera = window.__dbgCam;
      }
      if (p.cam) camera.position.set(p.cam[0], p.cam[1], p.cam[2]);
      if (p.look) camera.lookAt(p.look[0], p.look[1], p.look[2]);
      else camera.lookAt(0, 0, 0);
      world.updateMatrixWorld(true);
    } else if (!reduced) {
      const cx = Math.sin(now / 9000) * 0.12;
      const cy = Math.cos(now / 11000) * 0.10;
      camera.position.set(CAM_POS[0] + cx, CAM_POS[1] + cy, CAM_POS[2]);
      camera.lookAt(CAM_LOOK[0], CAM_LOOK[1], CAM_LOOK[2]);
    }

    renderer.render(scene, camera);
    // Sanctioned edit: capture the id so dispose() can cancel the loop. Skip the
    // reschedule under reduced-motion so we hold a single resolved frame.
    if (!reduced && !disposed) rafId = requestAnimationFrame(tick);
  }

  // ---------- Responsive right-margin placement ----------
  // Keep the stack's right edge a consistent distance off the right viewport
  // edge on EVERY aspect ratio: the empty margin is held at ~1/3 of the
  // previous revision's margin, with a safety floor that guarantees the static
  // pile — and therefore the flipping page, whose rightmost reach is always
  // just *inside* the pile's (measured) — is never cropped during the 270°
  // flip. Because the flip never extends further right than the pile, holding
  // a positive pile margin is sufficient; no frustum/FOV change is needed and
  // the canvas already spans the full viewport width.
  //
  // Everything is solved in camera-space X ("viewX"); the right frustum edge
  // sits at viewX = FRUSTUM * aspect / 2. Nothing is hard-coded — the pile
  // extent and the (ΔviewX / Δworld-x) gain are measured live, so this stays
  // correct if the geometry, camera, or rotation ever change.
  const _camInv = new THREE.Matrix4();
  const _tmpV   = new THREE.Vector3();
  const camX = (x, y, z) => _tmpV.set(x, y, z).applyMatrix4(_camInv).x;
  function refreshCamInv() {
    camera.updateMatrixWorld(true);
    _camInv.copy(camera.matrixWorld).invert();
  }
  function pileMaxViewX() {
    world.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(pileGroup);
    let m = -Infinity;
    for (const x of [box.min.x, box.max.x])
      for (const y of [box.min.y, box.max.y])
        for (const z of [box.min.z, box.max.z]) {
          const vx = camX(x, y, z);
          if (vx > m) m = vx;
        }
    return m;
  }

  // Anchor the ÷3 target to the PREVIOUS revision's margin (rot 12.6°, x 2.4)
  // — i.e. the empty space the user was actually looking at.
  let ORIG_PILE_VIEWX = 0;
  (function calibrateOriginalMargin() {
    refreshCamInv();
    const keepRot = world.rotation.y, keepX = world.position.x;
    world.rotation.y = 0.22;   // pre-rotation
    world.position.x = 2.4;    // pre-shift
    ORIG_PILE_VIEWX = pileMaxViewX();
    world.rotation.y = keepRot; // restore shipped pose
    world.position.x = keepX;
    world.updateMatrixWorld(true);
  })();

  function positionStackForAspect() {
    // Fixed cinematic framing now — the perspective rig is tuned to a specific
    // composition, so we no longer re-seat the stack per aspect ratio.
    world.updateMatrixWorld(true);
  }

  // ---------- Resize ----------
  function resize() {
    renderer.setSize(cw(), ch(), false);
    camera.aspect = cw() / ch();
    camera.updateProjectionMatrix();
    refreshRects();
  }
  window.addEventListener('resize', resize);
  // A ResizeObserver on the canvas re-seats the stack whenever its box changes
  // — including the initial post-layout settle and any container resize — so
  // the ÷3 right margin (and the no-crop guarantee) hold at the ACTUAL display
  // aspect in every environment, not just whatever size existed at boot.
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => resize());
    resizeObserver.observe(canvas);
  }
  // Also refresh rects after fonts load (the .id element may grow once Geist Mono
  // swaps in). Guard against a late resolve after unmount touching a torn-down scene.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => { if (!disposed) refreshRects(); });
  }

  // Boot
  positionStackForAspect();
  world.updateMatrixWorld(true);
  applyFlip(0);
  refreshRects(); // seed canvas/span rects before first frame (reduced-motion draws immediately)
  // Telemetry overlay starts fully hidden — nothing visible until the flip lands.
  spanAnchor.style.opacity = 0;
  svgLine.style.opacity = 0;
  if (process.env.NODE_ENV !== 'production') {
    window.__hero = { scene, camera, renderer, world, flipTranslate, flipRotate, pileGroup, targetWorld, tick, applyFlip, applyCurl, positionStackForAspect, advancePage, getActiveIndex: () => activeIndex };
  }
  rafId = requestAnimationFrame(tick);

  // ---------- Teardown (React unmount / StrictMode double-invoke) ----------
  return function dispose() {
    if (disposed) return; // re-entrancy / double-call guard
    disposed = true;
    if (rafId) cancelAnimationFrame(rafId);
    window.removeEventListener('resize', resize);
    if (resizeObserver) resizeObserver.disconnect();
    // Release GPU resources: geometries, materials, and any textures they hold.
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      const mat = obj.material;
      if (mat) {
        const mats = Array.isArray(mat) ? mat : [mat];
        for (const m of mats) {
          for (const key in m) {
            const val = m[key];
            if (val && val.isTexture) val.dispose();
          }
          if (m.dispose) m.dispose();
        }
      }
    });
    renderer.dispose();
    // Force-drop the WebGL context now rather than waiting for GC — prevents
    // "Too many active WebGL contexts" across route changes / StrictMode remounts.
    if (renderer.forceContextLoss) renderer.forceContextLoss();
    if (process.env.NODE_ENV !== 'production') {
      delete window.__hero;
      delete window.__L;
    }
  };
}
