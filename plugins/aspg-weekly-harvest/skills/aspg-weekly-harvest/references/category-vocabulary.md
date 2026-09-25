# ASPG category vocabulary, profit centers, and the contribute/proposeEntity contract

This is the fixed vocabulary the harvest step classifies every proposal into
— taken from the CTO's `Demo_Contribution_Review_Page.html` (`CATEGORIES` /
`CATEGORY_TO_ENTITY_TYPE` constants). Seven values, rarely if ever grows;
"Team"/"Portfolio" were deliberately removed (2026-08-07) in favor of the
profit-center field carrying that meaning instead.

| category value    | label             | entity type (for `proposeEntity`) |
|--------------------|-------------------|------------------------------------|
| `customer_active`  | Customer Active   | `customer`                         |
| `customer_prospect`| Customer Prospect | `market`                           |
| `customer_former`  | Customer Former   | `customer`                         |
| `partner`          | Partner           | `partner`                          |
| `competitor`       | Competitor        | `competitor`                       |
| `contact`          | Contact           | `market`                           |
| `vocabulary`       | Vocabulary        | `market`                           |

Category and profit center are **not** either/or. Set a profit center
whenever a specific SPG team clearly owns/delivers the fact, even for a
customer-primary one — it is extra routing info alongside the entity, not a
replacement for it. The reviewer's own account's profit center is not
knowable to the harvest step in advance; use `mcp-aspg_suggestProfitCenter`
per candidate to pre-fill a guess, and let the review page's dropdown be the
correction point. The tool's own docs say it is "informational only, never
auto-applied" — never skip showing the dropdown on the strength of the
suggestion alone.

## Entity-existence check

Before flagging a proposal `needs_new_entity`, call `mcp-aspg_resolve(name)`.
Only flag it when there is truly no resemblance — `proposeEntity` itself
auto-creates only in that case; anything with even a below-threshold
resemblance is held for the CTO's weekly duplicate review instead of risking
a silent duplicate or a silent wrong-merge. Don't pre-empt that judgment by
being either over-eager or over-cautious with the flag — when unsure, leave
`needs_new_entity` unset and let the reviewer's own read of `resolve`'s
candidates decide (the review page still lets them mark it manually).

## The two tools this skill calls, and what they actually take

`mcp-aspg_contribute`:

- `entity` (string, required) — free text; ASPG resolves it server-side.
  Never hand it a raw internal id — that's `aspg_resolve`'s job elsewhere,
  not needed here.
- `fact` (string, required) — one neutral sentence. There is no separate
  `category` or `profit_center` field on this tool, so fold that context
  into the sentence itself as a parenthetical, matching the CTO's own
  established wording:
  `"<headline>. <detail> (SPG profit center: <name>, code <code>) (confidence: <level>) (open opportunity) (source: <note>)"`
  — omit each parenthetical that doesn't apply (asserted confidence and no
  profit center produce the shortest form).
- `confidence` (string, default `"asserted"`) — maps 1:1 to the review
  page's confidence dropdown (`asserted` / `confirmed` / `rumor`).
- `source_note` (string, optional) — a short pointer (OneDrive/SharePoint
  share link, or a plain description like "Kickoff call, 10 Aug"), never the
  document itself.
- `as_of` (string, optional) — leave blank unless the harvest step has a
  concrete source date worth recording.
- `tags` (optional, shape undocumented) — do **not** guess a profit-center
  tag format here; the parenthetical in `fact` is the proven channel for
  that instead.

`mcp-aspg_proposeEntity`:

- `name` (string, required) — the entity name as it should be created.
- `type` (string, required) — from the table above, keyed by the row's
  `category`.
- `parent` (string, optional) — leave blank unless the harvest step actually
  knows a parent entity.

Auto-created immediately only when nothing at all resembles it in ASPG;
otherwise held for the CTO's weekly duplicate review. That's a decision the
tool itself makes — the skill's job is just to call it when a row is flagged
new, not to second-guess the result.
