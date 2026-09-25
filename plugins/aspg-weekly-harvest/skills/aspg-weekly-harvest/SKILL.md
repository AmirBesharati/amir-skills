---
name: aspg-weekly-harvest
version: 1.4.0
description: "ASPG Weekly Harvest. Replaces the copy-paste 'Weekly_Harvest_Starter_Prompt.txt' step from the ASPG v3 Contribution Guide with a skill that scans the last 7 days of Outlook mail/calendar/Teams itself, classifies candidate facts (customer/partner signals, opportunity signals, team/people signals, contact signals, vocabulary signals), pre-fills entity-existence and profit-center guesses via ASPG's own tools, and renders a review page with checkboxes and editable wording. The review page's Contribute button attempts a one-click direct submit via the Artifact mcp capability, addressed as the plain connector display name (a host: Desktop-Extension addressing was tried in between and is confirmed dead — see references/mcp-capability.md); on any failure it falls back per-row to a paste-back text block for the chat, and a read-only 'Check connection' diagnostic stays in the page either way. Use when someone asks to 'run my ASPG weekly harvest', 'check what I have to contribute to ASPG this week', 'do my ASPG weekly review', or references the Weekly_Harvest_Starter_Prompt. NOT for the 5-second ad-hoc mode ('Contribute to ASPG: ...') — that already works fine as a plain sentence and this skill doesn't touch it. NOT a replacement for the CTO's own contribution-guide pack or its confidentiality policy — this skill defers to that pack's wording for what's excluded and re-uses ASPG's own server-side filter as the real gate."
metadata:
  requires:
    mcp: []
    bins: []
---

# ASPG Weekly Harvest

Turns the ASPG v3 Contribution Guide's weekly habit from "paste a long prompt
every time" into a skill: scan → classify → enrich → render a review page →
one click (or, per-row wherever that fails, the same copy-paste chat step
as before). The one-click path is on its third attempt — see
`references/mcp-capability.md` for the full history: plain-name addressing
first, then a `host:` (Desktop Extension) addressing that turned out to be
dead (Claude Code refuses to even publish that manifest, and a live
`listTools()` call against it came back empty), so this reverts to plain-name
addressing and asks whether the original upstream failure still reproduces.

**Scope is deliberately narrow.** This skill owns the weekly-harvest →
review → contribute flow only. It does not reimplement the guide's 5-second
ad-hoc mode ("Contribute to ASPG: ...") — that's already a plain sentence,
not a real pain point, and adding ceremony to it would be pure overhead.

## First read

1. `references/harvest-signals.md` — the six signal categories and the
   strict exclusion list, verbatim from the CTO's own wording. Don't
   paraphrase the exclusion list; use it exactly.
2. `references/category-vocabulary.md` — the seven ASPG categories, the
   category→entity-type mapping for `proposeEntity`, and exactly what
   `mcp-aspg_contribute` / `mcp-aspg_proposeEntity` take as arguments.
3. `references/mcp-capability.md` — the one-click submit's history (plain
   connector name; `host:` addressing, confirmed dead; back to plain
   connector name, current), what the "Check connection" diagnostic still
   does, and why the connector name is hardcoded. Read this before ever
   changing `scripts/render_review_page.py`.

**DEV-ONLY, DELIBERATELY (2026-09-24).** This skill is still being
dogfooded. Prod ASPG (`mcp__SPG_MCP_Gateway__...`) is a shared knowledge
base other colleagues read from, and a bug here must never be able to write
fake or test harvest data into it. So, unlike a normal "don't hardcode tool
names" rule:

- **Only ever call tools under the dev connector**,
  `mcp__SPG_MCP_Gateway_Dev__mcp-aspg_*` (`_status`, `_resolve`,
  `_suggestProfitCenter`, `_contribute`, `_proposeEntity`).
- If a session has **both** a dev and a prod ASPG connector present (as is
  normal right now), always pick the one whose namespace segment contains
  `Dev` — never the other one, even if dev is temporarily erroring and prod
  would "just work."
- If **only** the prod-named tools are present (no `..._Dev` tools at all),
  **stop and say so plainly** — don't silently fall back to prod. Tell the
  person the dev connector isn't available in this session and that
  running against prod needs a deliberate config change first (see
  `references/mcp-capability.md`), not an automatic fallback.
- The review page's own Contribute button is pinned the same way via
  `MCP_CONNECTOR_NAME` inside `scripts/render_review_page.py` (currently
  `"SPG MCP Gateway Dev"`) — the manifest and every `mcp.server(...)` call in
  the page use this same plain display name directly, pinned for the
  identical reason.

**Before this skill goes anywhere near another colleague**, both pins (this
rule and `MCP_CONNECTOR_NAME`) need to be changed back to prod *on purpose*
— see `references/mcp-capability.md` for the exact steps. Until then, treat
"only dev tools are visible" as the expected, correct state, not something
to work around.

## Step 0 — access check, fails fast and plainly

Call the ASPG status tool (`..._status`). If it doesn't exist at all, the
person doesn't have the MCP SPG Gateway connector — tell them plainly and
stop. If it answers but `contribute` isn't in their access flags, tell them
plainly (point at Andreas, same as the guide does) and stop — there's no
point building a review page for facts that can't be submitted.

## Step 1 — M365 check

This workflow needs the Microsoft 365 connector (mail/calendar/Teams) to
scan anything. If those tools aren't available in this session, say so
plainly and stop — the 5-second ad-hoc mode still works fine without M365,
just not this weekly flow.

## Step 2 — scan and classify

Scan the last 7 days of mail, calendar/meetings, and Teams chats. Classify
into the six signal categories from `references/harvest-signals.md`,
applying the exclusion list *before* anything becomes a candidate — the
server-side filter on `mcp-aspg_contribute` is a second gate, not the only
one. Apply the naming check: full canonical/legal names where known, flagged
rather than guessed where not.

## Step 3 — enrich each candidate

For every candidate:

- Call `..._resolve(name)` to check whether the entity already exists.
  Flag `needs_new_entity` only when there's truly no resemblance — anything
  with even a below-threshold match goes to the CTO's own weekly duplicate
  review instead, per how `proposeEntity` itself behaves. When genuinely
  unsure, leave the flag unset; the review page still lets the person set it
  by hand.
- Call `..._suggestProfitCenter(text)` to pre-fill a profit-center guess.
  Treat it as a pre-fill only — the tool's own docs call it "informational
  only, never auto-applied," and the review page's dropdown is where the
  person corrects it.
- Map the category to its ASPG category value per
  `references/category-vocabulary.md`.

## Step 4 — write the harvest JSON

Shape matches `examples/sample_harvest.json` exactly (that file is FAKE data
for testing the script — never overwrite it with a real run's output). Write
the real harvest to its own path, e.g. `aspg-harvest-<window_end>.json` in
the current working directory — this is a weekly working file, not a
keeper document; overwriting last week's is fine.

## Step 5 — render

```bash
python3 .claude/skills/aspg-weekly-harvest/scripts/render_review_page.py \
  --harvest aspg-harvest-<window_end>.json \
  --out     aspg-review-<window_end>.html
```

The script aborts with a specific field/row name on any missing or invalid
field — fix the harvest JSON and rerun rather than patching the HTML by
hand.

## Step 6 — publish as an Artifact, not a local file

The one-click Contribute button only works when this page runs as a Claude
Artifact with the `mcp` capability declared, addressed as the plain
connector display name (see `references/mcp-capability.md` for why — a
`host:` addressing was tried and confirmed dead):

```
capabilities: {
  mcp: {
    servers: [
      { server: "SPG MCP Gateway Dev", tools: ["mcp-aspg_contribute", "mcp-aspg_proposeEntity"] }
    ]
  }
}
```

Publish the rendered HTML with the Artifact tool using exactly that
capability. Tell the person, in one short message: the page is ready, check
the boxes worth sharing, edit anything you want, hit Contribute — it
submits directly; if it doesn't work in their client, it'll hand back a
text block (per row, if only some fail) to paste into this same chat
instead. Ask them to also try the page's "Check connection" button if
anything looks wrong, and share what it reports — this addressing failed
consistently once before with an upstream consent error (see
`references/mcp-capability.md`), so the first live click after this revert
is the real test of whether that has changed.

## Step 7 — if a paste-back happens anyway

If some or all rows fell back (client doesn't support the `mcp` capability
this way, or a call failed), treat whatever comes back in chat exactly like
today's ad-hoc "Contribute to ASPG: ..." messages — call `proposeEntity`
then `contribute` per line, same as always. No new logic needed there.

## What this skill deliberately does not do

- Doesn't touch the 5-second ad-hoc mode.
- Doesn't fetch a live profit-center directory — relies on
  `suggestProfitCenter`'s own guess plus whatever static list the harvest
  step puts in the JSON. A live department lookup would be a reasonable
  future improvement, not something this version does.
- Doesn't fix the mislabeled real-customer-data sample file the CTO's
  README flagged (`SAMPLE_aspg-review-2026-08-07.html`) — that's Andreas's
  file to fix at the source, out of scope here entirely.
- Never auto-retries an ambiguous write failure (`server_unavailable` /
  `upstream_error`) — a fresh click from the person is required, per the
  `mcp` capability's own doctrine on writes.

## Before this goes to anyone else

The copy-paste fallback is confirmed working end-to-end on dev: a real
entity created (`ROTHWALD-FENSTERBAU`) and a real fact filed and confirmed
searchable, correctly attributed. The one-click path, back on plain-name
addressing after `host:` was confirmed dead, previously failed live on this
same addressing with a consistent `upstream_error` ("connector access isn't
confirmed for this artifact right now") — see `references/mcp-capability.md`
for the full record. **Re-test live before trusting it** — that failure may
or may not still reproduce. Before this goes near another colleague, either
way, the dev pins still need to change to prod, on purpose — see that same
file for the exact steps, and the "First read" section above for the
tool-selection rule that has to change alongside it.
