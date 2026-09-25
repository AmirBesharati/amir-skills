# What counts as a harvest signal

Source: adapted from the CTO's own `Weekly_Harvest_Starter_Prompt.txt` (ASPG v3
Contribution Guide pack, 2026-09-18). Keep this file in sync if that pack is
ever revised — it is the canonical wording, not a paraphrase.

Scan the last 7 days of the person's Outlook mail, calendar/meetings, and
Teams chats. Pull out anything worth sharing to ASPG, sorted into:

1. **Customer / partner signals** — a named customer, partner, or prospect
   said/decided/needs something: strategy shifts, pain points, competitive
   moves, buying signals, project status.
2. **Opportunity signals** — pipeline movement tied to a named customer: new
   interest, timeline change, stage change, decision-maker involvement.
   No amounts, no margins — see the exclusion list below.
3. **Team / people signals** — who covers what, new stakeholder contacts, org
   changes on the customer or SPG side — stated as role/fact, not opinion.
4. **Contact signals** — a new or changed key contact at a customer/partner
   (name, title, who covers the account). A plain professional-contact fact
   is NOT an HR matter and is explicitly wanted, not excluded.
5. **Vocabulary signals** — the same entity referred to by two different
   names/spellings, or an informal/short name in use — worth flagging for
   the entity-alias registry.
6. **Naming check** (applies to everything above) — for every entity
   mentioned, use its full canonical/legal name where known. If unsure of
   the correct spelling, flag it — never guess.

## Never include — drop before the candidate ever reaches the review page

- Pricing / commercials
- M&A / valuation / ownership
- Compensation / payroll
- HR matters about a named individual (performance opinions, personal
  travel/leave — not the same as a plain contact fact above)
- Legal disputes
- Anything about SPG's own ownership structure

This is a first filter, not the only one — `mcp-aspg_contribute` re-scrubs
every fact server-side regardless of what passed this step. Both layers must
agree before anything reaches the review page; when in doubt, drop the
candidate rather than let a human catch it at review time.

## Per-candidate fields to produce

One line per fact: category (see `category-vocabulary.md`), entity, the
headline, supporting detail, source (mail/meeting/chat + date), and
confidence (`asserted` / `confirmed` / `rumor`). These map directly onto the
`proposals[]` entries the render script (`scripts/render_review_page.py`)
expects — see `examples/sample_harvest.json` for the exact shape.
