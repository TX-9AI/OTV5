# docs/VISION.md — v4.0 — what a successful OTV4 looks like

**Opened 2026-08-19.**

---

## THE BOTTOM LINE

**P&L and return on risk. Dollars.**

Not label accuracy. Not acceptance rows. Not conviction. Not win rate.

---

## WHAT "WORKING" MEANS

**A demonstrable edge, evidenced by NOT LOSING MONEY over a measurable period.**

Not a good week — a stretch long enough that variance cannot explain it. The
question is never *"did today make money"*; it is *"is there something here that
would still be here next month."*

**There will be bad trades and bad days. That is not failure.** The requirement
is that they are **overshadowed** by the winning ones.

---

## ⚠️ WIN RATE IS EXPLICITLY NOT THE TARGET

Operator, 2026-08-19: *"You don't need a high win rate if you have good stop
discipline & smart management of winners."*

**OTV3 proved this from two directions, and both are worth carrying forward as
evidence rather than as opinion.**

**THE EXITS WERE THE EDGE.**
· `orb_trail_stop` — 107 trades, **95% win, +$37,848**
· `theta_bleed` — 107 trades, **100% win**
· `continuation_trail` — 149 trades, **85% win, +$27,884**
These never consulted the classifier. They managed what was already open.

**AND GRADING ENTRIES HARDER MADE MONEY WORSE.**
The setup scorer's A-grade: **399 trades, −$8,244** at 1.5× size.
Its B-grade: **220 trades, +$1,893**.
**Selection was never the lever. Management was.**

A 45%-win book with disciplined stops and managed winners beats a 60%-win book
that gives its gains back — and OTV3 measured exactly that giveback in its
NEVER-FAVOURABLE vs GAVE-IT-BACK split.

---

## SO OTV4 IS JUDGED ON

1. **Cut losers fast.** The stop is not a formality; it is where the edge is.
2. **Let winners run, and manage them.** The trail is the product.
3. **Fire only where structure earns it.** Fewer, better-founded entries beat a
   permissive engine with a clever-sounding filter.
4. **Size on evidence, not on confidence.** Flat until a scorer is earned.

---

## ⚠️ THE ANTI-GOAL, RECORDED SO IT CANNOT BE REPEATED

**OTV3 optimised a label and never measured dollars until the labels were
already trusted.**

Two months of good engineering went into Layer 1 acceptance rows, conviction
integration and ramp calibration — all measuring the engine against **its own
outputs**. The first non-circular test of whether the labels predicted anything
was run on **2026-08-19**, and it returned 44.9% direction accuracy: worse than
a coin.

**OTV4 measures dollars first and lets the labels earn their place afterwards.**

Every gate ships **LOG-ONLY** and is judged on outcomes before it is allowed to
refuse a trade. Every threshold is a **stated prior** until measurement replaces
it. And a number that has never been tested against P&L does not size anything.
