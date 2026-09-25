# The review page's one-click Contribute button — all three addressings confirmed dead

The CTO's original design (`Demo_Contribution_Review_Page.html`) is
deliberately a "dumb" static file: no backend, no network call, ever — the
Contribute button just assembles a text block the person pastes back into
their Claude chat, and Claude calls `mcp-aspg_contribute` from there.

**Attempt #1** (2026-09-24, removed 2026-09-25): called
`mcp-aspg_contribute` / `mcp-aspg_proposeEntity` directly via the `mcp`
capability, addressed as a plain connector name (`"SPG MCP Gateway Dev"`).
Failed consistently — see "Attempt #1 record" below — and was removed at
the user's explicit instruction.

**Attempt #2** (2026-09-25): the user asked to re-implement it.
This repo's own marketplace manifest
(`spg-claude-skills/.claude-plugin/marketplace.json`) says "MCP servers are
distributed separately via Desktop Extensions (.mcpb)." If this connector
is genuinely a Desktop Extension rather than a standard OAuth cloud
connector, the `mcp` capability addresses it differently: as a `host:<name>`
server, reached through the Claude Desktop app rather than a cloud
connector broker. Attempt #1 never tried that addressing — every call used
the plain connector name. Attempt #2 uses it instead:

```
capabilities: {
  mcp: {
    servers: [
      { server: "host:SPG_MCP_Gateway_Dev", tools: ["mcp-aspg_contribute", "mcp-aspg_proposeEntity"] }
    ]
  }
}
```

`host:SPG_MCP_Gateway_Dev` was computed the same way `MCP_CONNECTOR_NAME` is
used now — never hand-typed, so it couldn't drift out of sync — but this
addressing is no longer in the code (see "Confirmed dead" below).

**Blocked at publish time (2026-09-25, first Claude Code session):**
publishing an artifact with `server: "host:SPG_MCP_Gateway_Dev"` in the
manifest was rejected outright, from Claude Code, at publish time:

> `"host:SPG_MCP_Gateway_Dev" names a locally-configured MCP server, and
> host servers aren't available in this session — declare only claude.ai
> connectors`

**Confirmed dead, not just untestable (2026-09-25, second Claude Code
session):** re-verified the exact same publish-time rejection, byte-for-byte
(a fresh minimal test artifact declaring `host:SPG_MCP_Gateway_Dev` was
refused with identical wording). Then, since the artifact tool itself
refuses to even discuss whether it *works* for a Desktop-app viewer, a
second minimal test artifact was published declaring **both** addressings
side by side (`SPG MCP Gateway Dev` succeeds at publish; `host:...` still
rejected in the same call, so that entry had to be dropped to publish at
all) and opened live in the real Claude Desktop app:

```
listTools(SPG MCP Gateway Dev)      => OK, {servers: [{server: "SPG MCP Gateway Dev", authStatus: "unknown", ...}]}
listTools(host:SPG_MCP_Gateway_Dev) => OK, {servers: []}
```

`host:SPG_MCP_Gateway_Dev` doesn't error at runtime — it resolves to **no
server at all**. This connector is not exposed as a host-type (Desktop
Extension) bridge, regardless of what the marketplace manifest's "MCP
servers are distributed separately via Desktop Extensions" line suggested.
Combined with the permanent publish-time refusal, `host:` addressing for
this connector is now considered a closed question, not merely blocked from
one session type — no further host: testing is expected to help. The one
untested theory from the first pass (publish from an actual claude.ai/Desktop
**chat** rather than Claude Code) is superseded by this: even if a chat
session could get past the manifest step, the runtime evidence above shows
there'd be nothing on the other end to call.

**Attempt #3** (2026-09-25): with `host:` closed, the user asked to revert
to attempt #1's plain-name addressing and re-test live, since that was the
only addressing that ever actually reached the connector — the
`listTools()` evidence above confirms it still resolves to a real server.
`scripts/render_review_page.py` and `SKILL.md` are back to declaring
`{ server: "SPG MCP Gateway Dev", tools: [...] }` and calling
`mcp.server("SPG MCP Gateway Dev")` directly — no `host:` anywhere, and the
"Check connection" diagnostic now only checks this one addressing (checking
`host:` too would have been misleading noise now that it's a closed
question).

**Confirmed dead (2026-09-25):** re-tested live, in the actual Claude
Desktop app, with a real `contribute` click on a fake-data review page whose
manifest declared `{ server: "SPG MCP Gateway Dev", tools: [...] }` (this
time actually published with the capability present — the first Claude Code
attempt at this same test had accidentally shipped `capabilities: {}`, so
the code path was never exercised). Result: **the identical
`upstream_error`** ("connector access isn't confirmed for this artifact
right now") from the original attempt #1 record below, on the first fresh
click. Same failure, now reproduced twice, on two different published
artifacts, weeks apart in method — this is not an artifact-specific fluke or
a stale-manifest issue. All three addressings this skill has tried
(`host:`, and plain-name twice) are now closed questions for this
connector.

Known constraints on `host:` servers in general, per the capability's own
docs — kept for background, though moot for this specific connector now:

- Only works **inside the Claude Desktop app**, viewing the artifact
  top-level as its owner — never in a browser tab, an embedded drawer, or
  as anyone other than the artifact's owner.
- The app may pop its own confirmation dialog for a call not annotated
  read-only (both `contribute` and `proposeEntity` are writes), which can
  take a while or come back `cancelled` — treat `cancelled` as
  outcome-unknown, not a proof the call didn't run.

## What's still in the page regardless of outcome

The **"Check connection"** button — a read-only diagnostic
(`listTools()` against `MCP_CONNECTOR_NAME`, dumped via `dumpError()` /
`JSON.stringify`) — never calls `contribute` or `proposeEntity`, and stays
useful either way: to confirm the connection before trusting it with a real
harvest, or to gather evidence if a call fails.

**Why `"SPG MCP Gateway Dev"` specifically:** confirmed (2026-09-24) that
the connector is installed via a distributed extension file, so its display
name is fixed for everyone rather than something each person types (the
guide's own Step 1, "name it ASPG," is stale wording — don't treat it as
the source of truth). Two real connectors exist — prod (`"MCP SPG Gateway"`)
and dev (`"SPG MCP Gateway Dev"`) — and both the manifest and the harvest
step's own tool calls in `SKILL.md` stay pinned to dev only, so nothing in
this still-being-dogfooded skill can touch prod ASPG.

## Attempt #1 record, 2026-09-24/25: why the plain-name addressing was removed

Tested live against the dev connector, in the actual Claude Desktop app
(the guide's real audience), with real `contribute` access. Every
`mcp-aspg_contribute` call rejected with the same `upstream_error`, message
`"connector access isn't confirmed for this artifact right now"`, across
every attempt below.

Ruled out, in order, each with its own test:

1. **Consent race** (first call fires before the viewer answers the
   permission prompt) — ruled out: failed again after a full page reload,
   which should have started clean.
2. **Connector not actually registered at the account level** — ruled out:
   confirmed "SPG MCP Gateway Dev" is listed under the account's own
   Settings → Connectors (not just visible to Claude Code's own tools).
3. **Wrong client** (claude.ai web vs Desktop) — ruled out: tested directly
   in the Desktop app, the guide's actual target.
4. **An internal-network/VPN gate on the gateway** — ruled out on
   correction from the user: SPG has no VPN at all, so this was never the
   right explanation (an earlier version of this doc guessed it from the
   guide's own troubleshooting wording; that guess was wrong).
5. **Not actually following the retry contract** — ruled out: the raw
   error (captured via the page's "Check connection" / full-dump
   diagnostics) is `{code: "upstream_error", message: "connector access
   isn't confirmed for this artifact right now", server: "SPG MCP Gateway
   Dev", retryable: true, retryAfterMs: 30000}` — exactly the documented
   shape for "a first call on a connector whose consent the viewer could
   not give just then." Followed the doctrine precisely: same page (no
   reload), waited the full 30s `retryAfterMs`, then a fresh click — saw
   the actual consent/"Review in Claude" prompt this time, approved it, and
   got the **identical** error again, byte-for-byte, immediately after
   approving.

**Conclusion that led to removing attempt #1:** with every client-side
remediation exhausted — correct wait, fresh gesture, explicit approval,
repeated — and the error never changing shape, this pointed to a genuine
platform-side gap, specifically the plain connector-name addressing not
being appropriate for how this connector is actually registered. Attempt
#2 (`host:` addressing, above) is the direct response to that theory.

**What was confirmed working throughout, and remains the only working
path:** the copy-paste flow end-to-end — a real entity created
(`ROTHWALD-FENSTERBAU`) and a real fact filed and confirmed searchable in
dev, correctly attributed. Since attempt #3 also failed, every row degrades
to this same paste-back text, per row, automatically — this is not a
fallback for a rare edge case anymore, it is the only path this skill has
ever gotten to actually work end-to-end. Any future one-click attempt needs
a new theory, not a fourth re-try of an addressing already tried twice.
