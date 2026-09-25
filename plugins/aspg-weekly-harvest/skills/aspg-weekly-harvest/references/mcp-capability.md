# The review page's one-click Contribute button — attempt #2 (host: addressing)

The CTO's original design (`Demo_Contribution_Review_Page.html`) is
deliberately a "dumb" static file: no backend, no network call, ever — the
Contribute button just assembles a text block the person pastes back into
their Claude chat, and Claude calls `mcp-aspg_contribute` from there.

**Attempt #1** (2026-09-24, removed 2026-09-25): called
`mcp-aspg_contribute` / `mcp-aspg_proposeEntity` directly via the `mcp`
capability, addressed as a plain connector name (`"SPG MCP Gateway Dev"`).
Failed consistently — see "Attempt #1 record" below — and was removed at
the user's explicit instruction.

**Attempt #2** (2026-09-25, current): the user asked to re-implement it.
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

`host:SPG_MCP_Gateway_Dev` is computed in `scripts/render_review_page.py`
(`MCP_HOST_SERVER`) from `MCP_CONNECTOR_NAME` via the `mcp` capability's own
sanitizing rule — anything outside `[A-Za-z0-9_-]` becomes `_` — never
hand-typed, so it can't drift out of sync.

**Blocked before it could even be tested (2026-09-25):** publishing this
artifact with `server: "host:SPG_MCP_Gateway_Dev"` in the manifest was
rejected outright, from this Claude Code session, at publish time:

> `"host:SPG_MCP_Gateway_Dev" names a locally-configured MCP server, and
> host servers aren't available in this session — declare only claude.ai
> connectors`

This is a restriction on the **publishing session**, separate from
anything about the viewer's session — Claude Code apparently can't declare
a `host:` manifest entry at all, regardless of whether it would resolve for
a Desktop-app viewer. The artifact was republished with the plain
`"SPG MCP Gateway Dev"` name in the manifest instead (attempt #1's
addressing) so it isn't left broken, but the page's JS still *calls*
`mcp.server(MCP_HOST_SERVER)` — since that name isn't in the manifest, that
call will reject `not_in_manifest` immediately, on every page load, before
a person even clicks anything. **Attempt #2 cannot be genuinely tested from
this session as currently set up.**

The one path that might still work: publishing (or republishing) this same
artifact from inside an actual claude.ai / Claude Desktop **chat**
conversation, rather than from Claude Code — if the "host servers aren't
available in this session" restriction is specific to Claude Code's own
publishing path rather than universal, a chat-published version might
accept the `host:` manifest entry where this session's Artifact tool call
would not. Untested — flag this to whoever picks this up next.

Known constraints on `host:` servers, per the capability's own docs — worth
knowing before reading too much into a failure:

- Only works **inside the Claude Desktop app**, viewing the artifact
  top-level as its owner — never in a browser tab, an embedded drawer, or
  as anyone other than the artifact's owner. Outside those conditions the
  call fails `server_not_connected` unconditionally, which would look
  identical to a genuine "no host bridge" failure — check the viewing
  conditions before concluding the addressing itself is wrong.
- The app may pop its own confirmation dialog for a call not annotated
  read-only (both `contribute` and `proposeEntity` are writes), which can
  take a while or come back `cancelled` — treat `cancelled` as
  outcome-unknown, not a proof the call didn't run.
- `listTools()` omits `host:` servers outside the app entirely (not even
  listed as `authStatus: "unknown"`) — the "Check connection" button now
  checks both `MCP_CONNECTOR_NAME` and `MCP_HOST_SERVER` side by side,
  which itself is a useful signal: if only one of the two lists at all,
  that tells you which addressing this client actually recognizes.

## What's still in the page regardless of outcome

The **"Check connection"** button — a read-only diagnostic
(`listTools()` against both addressings, dumped via `dumpError()` /
`JSON.stringify`) — never calls `contribute` or `proposeEntity`, and stays
useful either way: to confirm attempt #2 before trusting it with a real
harvest, or to gather evidence if it also fails.

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

**What was confirmed working throughout, and remains the fallback:** the
copy-paste flow end-to-end — a real entity created
(`ROTHWALD-FENSTERBAU`) and a real fact filed and confirmed searchable in
dev, correctly attributed. If attempt #2 also fails, every row degrades to
this same paste-back text, per row, automatically.
