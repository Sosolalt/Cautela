## Inspiration

In 2020, Bristol-Myers Squibb missed an FDA deadline by 36 days. One contingent-value-right clause — buried in a merger agreement someone was paid to read — cost Celgene shareholders roughly $6.4 billion. Nobody hid it. Someone simply didn't click into it in time.

That is the quiet scandal of M&A due diligence. A mid-market deal takes 30 to 90 days, costs $50K–$200K, and burns associate time at $200–$500 an hour — most of it spent reading boilerplate where the answer is "fine." Attention is rationed, so the real deal-breakers slip through exactly where the budget ran out.

The obvious pitch is "AI reads contracts faster." We rejected it. Faster-wrong is still wrong, and no general counsel stakes a $500M acquisition on a black box. The blocker to adoption was never speed — it was accountability.

**And that is exactly the gap in the market.** Vertical legal-AI tools already exist — Harvey, Kira, Luminance. What none of them ships is an honest answer to the one question a general counsel actually asks: *"How do you know?"* They give you the finding. They don't give you the evidence that the finding is right, the trace of how it was reached, or a way to catch the model when it's confidently wrong. That answer is precisely what an observability spine makes possible — and it's why we built Cautela on Arize Phoenix rather than bolting a dashboard on at the end.

So we built Cautela on a harder thesis: not *AI does M&A review faster*, but **AI does M&A review with an audit trail you can click into**. Every clause it reads, every risk it flags, every decision to clear or escalate is traced, scored, and annotated in Arize Phoenix — and surfaced as a deep-link a lawyer, or a judge, can open and interrogate span by span. Phoenix is what lets us *answer the "how do you know?"* — hallucination and faithfulness scored on every finding, every prompt promotion gated behind an experiment, every citation graded against a gold set. The product isn't the answer. The product is the evidence behind the answer.

## What it does

Cautela reads a merger agreement and tells you what could kill the deal — with the exact words highlighted on the page.

Feed it an 8-K Exhibit 2.1 in the hosted demo, or any PDF locally. It parses every clause *with bounding-box coordinates*, then runs four classifiers in parallel — change-of-control, anti-assignment, MAC carve-out narrowing, accelerated vesting. It resolves cross-references between the Definitions section and the operative clauses, then emits Risk Findings with **verbatim cited spans** — never a paraphrase you have to trust.

Here is the part that earns trust: a deterministic Python Router — *not* an LLM — sorts every finding into three lanes: Auto-Clear, Escalate to Lawyer, or Block. The gates are independent, so a hallucinated explanation can never auto-clear, no matter how confident it sounds. Every decision lands in Arize Phoenix as span annotations you open in one click from the findings pane.

It also gets sharper on its own. A nightly Reflector loop reads its own escalation traces through Phoenix, drafts a candidate prompt, and promotes it only when the statistics earn it.

Then it zooms out. A fifth agent, the Portfolio Analyst, makes a single **Gemini 3.1 Pro** call across all 30 demo contracts at once — roughly 800k tokens — and returns a cross-deal cluster taxonomy: which MAC templates the portfolio falls into, which deal is the outlier, the representative clause per cluster. Per-contract vendors like Harvey and Kira don't do this.

## How we built it

The spine is a six-stage Google ADK topology: **Parser → Classifier (a ParallelAgent fan-out) → CrossReference → RiskJudge → Router → Reporter,** with the four risk classifiers fanned out to run concurrently.

We split the model tier deliberately, because cost was the binding constraint, not capability. The per-contract review pipeline runs on **Gemini 3.5 Flash** (GA), pinned via env — it carries the structured extract/classify/judge work at the accuracy our eval rail demands (held-out Block-recall 1.0) for roughly an order of magnitude less than the Pro preview, whose large-context pricing on a 150K-token merger agreement made per-review cost untenable. We reserve **Gemini 3.1 Pro** for the two places its 1M-context reasoning actually pays for itself: the Portfolio Analyst and the Reflector. The architecture is model-agnostic — every stage reads its model from env, so any deployment can dial a stage up to Pro without touching code. Files under 8MB inline via `Part.from_bytes`; larger PDFs route through Gemini's Files API and polled `Part.from_uri`, which stops the silent truncation that otherwise hits past page 20.

**Arize Phoenix is the spine, not a dashboard.** Self-hosted on Cloud Run, it carries OpenInference tracing on every ADK call. Inline `phoenix.evals` classifiers score each finding for hallucination and clause-faithfulness; those land back as programmatic span annotations the findings pane links straight into. It versions every prompt, gates promotions behind experiments, and grades citations against a gold set.

The standout is the **Reflector** — a Cloud Scheduler agent that reads its own traces back through the **Phoenix MCP** server, drafts a candidate prompt, and runs it as a Phoenix experiment. It auto-promotes *only if* a paired-bootstrap confidence-interval lower bound clears zero on an auto-growing regression dataset **and** it doesn't regress on a frozen held-out fold — with a code-enforced allowlist that physically refuses any write to that fold. Self-improvement that has to earn its promotion through statistics, not vibes.

Those statistics resample *contracts*, not findings — findings inside one contract are correlated, so the contract is the IID unit — under 5-fold cross-validation with a non-regression noise floor of $\epsilon = \max(\mathrm{SE},\, 0.03)$ and deployed routing thresholds of $\tau_h = 0.99 / \tau_f = 0.50$, tuned so a flag fires only on a concrete defect. Serving is FastAPI on Cloud Run (scales to zero off-demo), a Next.js 14 + Tailwind frontend with react-pdf and a Phoenix iframe deep-link, EdgarTools pulling the filings live, all on Vertex AI.

## Challenges we ran into

**The LLM lied about its own ecosystem.** Roughly 15 first-pass calls across ADK, the Phoenix client, Phoenix evals, and EdgarTools came back with confidently fabricated signatures — `provider="vertexai"` instead of `"vertex"`, `clf(...)` instead of `clf.evaluate({...})[0]`. Specialist reviewers caught every one against live docs. The lesson stuck: in an agent that sells trust, you cannot trust the agent that builds it.

**Our first self-improvement rule was a Goodhart trap.** We started promoting prompts on `delta > 0.05` over N=30 — pure noise wearing a lab coat, and a metric the system would happily learn to game. We tore it out and replaced it with the paired-bootstrap CI plus the frozen-fold check.

**The scariest bug was silent.** An early Router averaged the hallucination and faithfulness scores before routing — so a confident hallucination could mathematically average its way into Auto-Clear, the exact failure that loses deals. We rewrote the Router to gate the two signals independently and locked it down with a dedicated unit test. That single fix is the line between a demo and a product a lawyer can sign.

## Accomplishments that we're proud of

**Cautela catches every deal-breaker — and we can prove it.** On our human-validated Internal-30 gold set — 530 findings, validated by a practicing M&A lawyer and an analyst — held-out **Block recall is 1.000**, with a **cluster-bootstrap 95% lower bound of 1.000** and a conservative per-finding Wilson floor of **0.942**. Zero held-out misses, at our deployed thresholds.

The public benchmarks hold up under a microscope too: MAUD-MCQ exact-match of **99.8%** (macro), CUAD-Spans token-F1 of **0.413** (paper-comparable) at **AUPR 0.654** on a held-out test split, and citation-map coverage of **40/40**. And **571 pure-Python unit tests** with fixed seeds and zero live API calls keep every one of those numbers reproducible.

Nothing here is a happy accident. The plan converged through **four independent expert review rounds** — M&A domain, architecture, data strategy, timeline — scoring **9 / 9 / 9.2 / 8.5**. The code converged through **four more**, spanning legal, senior Python/ADK, a Phoenix engineer, an ML statistician, and an SRE. Our gold set has a real chain of custody: pre-labeled by two automated annotation cohorts, then validated in depth by the lawyer and analyst as annotators of record. When Cautela says "a lawyer can verify this," we built the evidence to back it — a self-improving loop that earns every promotion through an experiment, an 800k-token portfolio pass no per-contract tool attempts, and an observability spine where every claim is one click from its proof.

## What we learned

**Trust is an architectural property, not a model property.** No bigger model would have fixed our averaging bug — only an independent, deterministic gate could. The most important component in a trustworthy AI system is the part that is *not* AI. (And the corollary held on cost: the right model for the review pipeline turned out to be the *cheaper* one — Flash carries the structured work at the accuracy the eval rail demands, and we spend Pro only where its 1M context earns its keep.)

We learned that statistical honesty is harder than statistical sophistication. It's easy to ship a number that moves; it's hard to prove it moved for a real reason and not noise. Choosing the contract as the IID unit, and demanding a bootstrap CI clear zero before any self-promotion, forced us to design against our own optimism.

We learned that frontier models hallucinate their own APIs with total confidence — so the verification culture you build *around* a model matters as much as the model itself. And we learned the killer feature was never speed. It was the one-click path from a finding to the Phoenix span that justifies it. The moment a skeptic can audit the machine, the machine becomes worth using.

## What's next for Cautela

**From auditable review to auditable negotiation.** Today Cautela proves a clause is a risk. Next, it drafts the redline — the markup, the fallback language, the rationale — with the same span-level citation discipline, so every proposed edit carries its own audit trail.

We're expanding the classifier bank beyond the four headline risks into the full diligence checklist — indemnification caps, survival periods, regulatory and antitrust triggers — each a gated, independently-verified lane. The Portfolio Analyst grows from 30 contracts to a firm's entire deal history, turning cross-deal pattern detection into institutional memory no associate could hold in their head, and surfacing how risk language drifts across a market over time.

We'll open the audit trail to the people who live in it: lawyers annotating findings directly, those annotations feeding the nightly Reflector loop — every review becoming training signal. And the thesis scales far past mergers: credit agreements, commercial leases, licensing, regulatory filings are the same problem wearing different paper. The endgame is a due-diligence partner that gets measurably sharper every night — faster than a team of associates, and for the first time, every bit as accountable.
