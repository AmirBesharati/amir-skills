#!/usr/bin/env python3
"""Render an ASPG weekly-harvest review page from a harvest JSON file.

Same visual language and DOM shape as the CTO's own
Demo_Contribution_Review_Page.html (ASPG_V3_Contribution_Guide pack,
2026-09-18) — checkbox per row, editable headline/detail/entity, category /
confidence / profit-center dropdowns, an "open opportunity" toggle. The
Contribute button attempts a one-click direct submit through the `mcp`
capability, addressed as a `host:` (Desktop Extension) server this time —
see references/mcp-capability.md for why: a first attempt addressed as a
plain connector name failed consistently and was removed, and this repo's
own marketplace manifest says these MCP servers are distributed as Desktop
Extensions, which the `mcp` capability addresses differently. On any
failure, the button falls back per-row to exactly the CTO's original
behavior: assemble a paste-able text block for the chat.

Only the standard library. Python 3.9+.

    python3 render_review_page.py --harvest sample_harvest.json --out review.html

The renderer invents nothing. A missing required field or an unknown
category aborts with a message naming the row and the field — a half-built
review page looks finished and nobody notices the gap.
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CSS_PATH = HERE.parent / "assets" / "review-page.css"

# Keep these in sync with references/mcp-capability.md.
#
# DEV-ONLY, DELIBERATELY (2026-09-24): pinned to the dev connector so
# testing this skill can never write fake/test harvest data into prod ASPG.
# Before this skill goes anywhere near another colleague, this must change
# back to the real prod connector name on purpose.
MCP_CONNECTOR_NAME = "SPG MCP Gateway Dev"

# The `mcp` capability's own rule for a host: (Desktop Extension) server
# name: the display name with anything outside [A-Za-z0-9_-] replaced by
# `_`. Computed rather than hand-typed so it can never drift from
# MCP_CONNECTOR_NAME.
MCP_HOST_SERVER = "host:" + re.sub(r"[^A-Za-z0-9_-]", "_", MCP_CONNECTOR_NAME)

CONTRIBUTE_TOOL = "mcp-aspg_contribute"
PROPOSE_ENTITY_TOOL = "mcp-aspg_proposeEntity"

CATEGORIES = [
    ("customer_active", "Customer Active"),
    ("customer_prospect", "Customer Prospect"),
    ("customer_former", "Customer Former"),
    ("partner", "Partner"),
    ("competitor", "Competitor"),
    ("contact", "Contact"),
    ("vocabulary", "Vocabulary"),
]
CATEGORY_VALUES = {c for c, _ in CATEGORIES}
CATEGORY_TO_ENTITY_TYPE = {
    "customer_active": "customer",
    "customer_former": "customer",
    "customer_prospect": "market",
    "partner": "partner",
    "competitor": "competitor",
    "contact": "market",
    "vocabulary": "market",
}
CONFIDENCE_VALUES = {"asserted", "confirmed", "rumor"}
REQUIRED_PROPOSAL_FIELDS = ("category", "entity", "headline", "detail", "confidence")

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800'
    '&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_harvest(path: pathlib.Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        die(f"can't read harvest file {path}: {exc}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON: {exc}")

    proposals = data.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        die(f"{path}: 'proposals' must be a non-empty list")

    for i, p in enumerate(proposals):
        row = f"proposals[{i}]"
        for field in REQUIRED_PROPOSAL_FIELDS:
            if not p.get(field):
                die(f"{row}: missing required field '{field}'")
        if p["category"] not in CATEGORY_VALUES:
            die(f"{row}: unknown category '{p['category']}' (expected one of {sorted(CATEGORY_VALUES)})")
        if p["confidence"] not in CONFIDENCE_VALUES:
            die(f"{row}: unknown confidence '{p['confidence']}' (expected one of {sorted(CONFIDENCE_VALUES)})")
        needs_new = p.get("needs_new_entity")
        if needs_new is not None:
            if not isinstance(needs_new, dict) or not needs_new.get("name"):
                die(f"{row}: 'needs_new_entity' must be null or an object with a 'name'")

    data.setdefault("window_start", "")
    data.setdefault("window_end", "")
    data.setdefault("sources", "")
    data.setdefault("flag_note", None)
    data.setdefault("undefined_profit_center", "99")
    data.setdefault("profit_centers", [{"code": data["undefined_profit_center"], "name": "UNDEFINED"}])
    return data


def e(value: str) -> str:
    return html.escape(str(value), quote=True)


def json_for_script(data: dict) -> str:
    """json.dumps, safe to embed inside <script>...</script>."""
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("</script", "<\\/script")
        .replace("<!--", "<\\!--")
    )


def build_html(data: dict) -> str:
    css = CSS_PATH.read_text(encoding="utf-8")
    n = len(data["proposals"])
    data_json = json_for_script(data)

    flag_html = ""
    if data.get("flag_note"):
        flag_html = f'<div class="callout match" id="flag-callout"><div class="ct">Flagged</div><p>{e(data["flag_note"])}</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASPG weekly review</title>
{FONTS}
<style>
{css}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    <div class="kicker">ASPG Weekly Harvest &middot; Review Only</div>
    <h1 id="hero-h1">Your ASPG batch is ready &mdash; <span class="accent" id="hero-count">{n} proposal{'s' if n != 1 else ''}</span> waiting.</h1>
    <p class="lede" id="hero-lede">The weekly harvest pulled neutral, shareable facts from the last 7 days. <b>Nothing has been submitted.</b> Check the ones worth sharing, edit the wording if you like, then hit Contribute.</p>
    <div class="meta">
      <div class="c"><span>Window</span><strong id="meta-window">{e(data['window_start'])} &ndash; {e(data['window_end'])}</strong></div>
      <div class="c"><span>Proposals</span><strong id="meta-count">{n}</strong></div>
      <div class="c"><span>Sources</span><strong id="meta-sources">{e(data['sources'])}</strong></div>
      <div class="c"><span>Status</span><strong>awaiting review</strong></div>
    </div>
  </div>
</header>

<section class="reveal">
  <div class="wrap">
    <div class="mcp-banner" id="mcp-banner"></div>

    <div class="sec-head"><h2>Proposals</h2></div>
    <p class="sec-sub">One fact per card. <span class="hint">Click the company name, headline, or detail to edit any of them, and pick the right category/confidence/profit-center from the dropdowns</span> before contributing &mdash; whatever's showing when you hit Contribute is what gets submitted, not the original. Category and profit center aren't either/or: set the profit center whenever a specific SPG team clearly owns/delivers the fact, even for a customer-primary one.</p>

    <div class="legend">
      <span class="item"><i class="dot blue"></i> confidence: asserted</span>
      <span class="item"><i class="dot green"></i> confidence: confirmed &nbsp;/&nbsp; submitted to ASPG</span>
      <span class="item"><i class="dot amber"></i> confidence: rumor</span>
      <span class="item"><i class="dot orange"></i> couldn't submit &mdash; see the card's own message</span>
    </div>

    <div class="plist" id="plist"></div>

    {flag_html}

    <div class="callout sky">
      <div class="ct">How this works</div>
      <p id="how-it-works-text">Checked = will be contributed. Uncheck anything you'd rather skip, edit any wording, then press <strong>Contribute</strong> below.</p>
    </div>

    <div class="callout match">
      <div class="ct">About the "Source" field</div>
      <p>Optional &mdash; paste a link to the OneDrive/SharePoint document this fact came from, if you have one; leave it blank otherwise. ASPG only ever stores the link, never the document.</p>
    </div>

    <div class="actionbar">
      <span class="count"><strong id="sel-count">0</strong> / <span id="sel-total">0</span> selected</span>
      <div class="spacer"></div>
      <button class="linkbtn" id="btn-all">Select all</button>
      <button class="linkbtn" id="btn-none">Select none</button>
      <button class="linkbtn" id="btn-check">Check connection</button>
      <button class="go" id="btn-go">Contribute &rarr;</button>
    </div>

    <div class="output" id="output">
      <div class="ct"><span id="output-title">Paste this into your Claude chat</span><button class="copybtn" id="btn-copy">Copy</button></div>
      <textarea id="output-text" readonly></textarea>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Internal document &mdash; Specific Group. Not for distribution.</p>
    <p>ASPG Weekly Harvest &middot; nothing submits without your click</p>
  </div>
</footer>

<script>
const DATA = {data_json};
const MCP_CONNECTOR_NAME = {json.dumps(MCP_CONNECTOR_NAME)};
const MCP_HOST_SERVER = {json.dumps(MCP_HOST_SERVER)};
const CONTRIBUTE_TOOL = {json.dumps(CONTRIBUTE_TOOL)};
const PROPOSE_ENTITY_TOOL = {json.dumps(PROPOSE_ENTITY_TOOL)};
const CATEGORY_TO_ENTITY_TYPE = {json.dumps(CATEGORY_TO_ENTITY_TYPE)};

function esc(s) {{ return String(s).replace(/"/g, '&quot;'); }}

const CATEGORIES = {json.dumps(CATEGORIES)};

const UNDEFINED_PC = DATA.undefined_profit_center;
const _pcSource = DATA.profit_centers || [];
const pcList = _pcSource.some(pc => pc.code === UNDEFINED_PC)
  ? _pcSource
  : [{{code: UNDEFINED_PC, name: "UNDEFINED"}}, ..._pcSource];
const pcNameByCode = Object.fromEntries(pcList.map(pc => [pc.code, pc.name]));

const plist = document.getElementById('plist');
DATA.proposals.forEach((p, i) => {{
  const n = i + 1;
  const card = document.createElement('div');
  card.className = 'prop';
  card.dataset.index = n;

  const isNew = !!p.needs_new_entity;
  const entityName = isNew ? p.needs_new_entity.name : p.entity;
  const catOptions = CATEGORIES.map(([v, l]) =>
    `<option value="${{v}}"${{v === p.category ? ' selected' : ''}}>${{l}}</option>`).join('');
  const pcInitial = (p.profit_center && p.profit_center.code) || UNDEFINED_PC;
  const pcOptions = pcList.map(pc =>
    `<option value="${{esc(pc.code)}}"${{pc.code === pcInitial ? ' selected' : ''}}>${{esc(pc.name)}}${{pc.code !== UNDEFINED_PC ? ' (' + pc.code + ')' : ''}}</option>`).join('');
  const isOpp = !!p.is_opportunity;

  card.innerHTML = `
    <div class="rail">
      <div class="num">${{String(n).padStart(2,'0')}}</div>
      <label class="cb-wrap"><input type="checkbox" class="cb" checked><span>Contribute</span></label>
    </div>
    <div class="body">
      <div class="cat-row">
        <select class="cat-select" data-orig="${{p.category}}">${{catOptions}}</select>
        <select class="conf-select ${{p.confidence}}" data-orig="${{p.confidence}}">
          <option value="asserted"${{p.confidence==='asserted'?' selected':''}}>asserted</option>
          <option value="confirmed"${{p.confidence==='confirmed'?' selected':''}}>confirmed</option>
          <option value="rumor"${{p.confidence==='rumor'?' selected':''}}>rumor</option>
        </select>
        <select class="pc-select" data-orig="${{pcInitial}}">${{pcOptions}}</select>
        <label class="opp-label"><input type="checkbox" class="opp-check" data-orig="${{isOpp}}"${{isOpp ? ' checked' : ''}}><span>Open opportunity</span></label>
      </div>
      <div class="ent-row">
        <span class="ent-edit" contenteditable="true" data-orig="${{esc(entityName)}}" data-is-new="${{isNew}}">${{entityName}}</span>
      </div>
      <h3 contenteditable="true" data-orig="${{esc(p.headline)}}">${{p.headline}}<span class="edited-pill">edited</span></h3>
      <p class="detail" contenteditable="true" data-orig="${{esc(p.detail)}}">${{p.detail}}</p>
      <div class="source-row">
        <span class="source-label">Source</span>
        <span class="source-edit" contenteditable="true" data-orig="${{esc(p.source_note || '')}}" data-placeholder="Click here and paste the link to a OneDrive/SharePoint source document">${{esc(p.source_note || '')}}</span>
      </div>
      <div class="row-status" id="row-status-${{n}}"></div>
    </div>`;
  plist.appendChild(card);

  const cb = card.querySelector('.cb');
  cb.addEventListener('change', () => {{ card.classList.toggle('off', !cb.checked); updateCount(); }});
  card.querySelector('.cat-select').addEventListener('change', () => markEdited(card));
  const confSel = card.querySelector('.conf-select');
  confSel.addEventListener('change', () => {{ confSel.className = 'conf-select ' + confSel.value; markEdited(card); }});
  card.querySelector('.pc-select').addEventListener('change', () => markEdited(card));
  card.querySelector('.opp-check').addEventListener('change', () => markEdited(card));
  card.querySelectorAll('[contenteditable]').forEach(el => {{
    el.addEventListener('blur', () => markEdited(card));
    el.addEventListener('paste', (ev) => {{
      ev.preventDefault();
      const cd = ev.clipboardData || window.clipboardData;
      const htmlData = cd.getData('text/html');
      const plain = cd.getData('text/plain');
      let text = plain;
      const m = htmlData && htmlData.match(/<a[^>]+href=["']([^"']+)["']/i);
      if (m) text = m[1];
      if (text) document.execCommand('insertText', false, text);
    }});
  }});
}});

function markEdited(card) {{ card.classList.add('edited'); }}

function updateCount() {{
  const total = document.querySelectorAll('.cb').length;
  const checked = document.querySelectorAll('.cb:checked').length;
  document.getElementById('sel-count').textContent = checked;
  document.getElementById('sel-total').textContent = total;
}}
updateCount();

document.getElementById('btn-all').addEventListener('click', () => {{
  document.querySelectorAll('.cb').forEach(cb => {{ cb.checked = true; cb.dispatchEvent(new Event('change')); }});
}});
document.getElementById('btn-none').addEventListener('click', () => {{
  document.querySelectorAll('.cb').forEach(cb => {{ cb.checked = false; cb.dispatchEvent(new Event('change')); }});
}});

function readRow(card) {{
  const i = parseInt(card.dataset.index, 10) - 1;
  const p = DATA.proposals[i];
  const h3Clone = card.querySelector('h3').cloneNode(true);
  const pill = h3Clone.querySelector('.edited-pill');
  if (pill) pill.remove();
  const headline = h3Clone.textContent.trim();
  const detail = card.querySelector('.detail').innerText.trim();
  const category = card.querySelector('.cat-select').value;
  const confidence = card.querySelector('.conf-select').value;
  const pcCode = card.querySelector('.pc-select').value;
  const isOpportunity = card.querySelector('.opp-check').checked;
  const entEl = card.querySelector('.ent-edit');
  const entityName = entEl.innerText.trim();
  const sourceEditEl = card.querySelector('.source-edit');
  const sourceLinkEl = sourceEditEl.querySelector('a');
  const sourceNote = (sourceLinkEl ? sourceLinkEl.href : sourceEditEl.innerText).trim();
  const needsNew = entEl.dataset.isNew === 'true';
  return {{ p, headline, detail, category, confidence, pcCode, isOpportunity, entityName, sourceNote, needsNew }};
}}

// Full paste-format line, kept identical to the CTO's original demo convention
// (category prefix + every parenthetical inline) -- used ONLY for the
// copy-paste fallback, where a human + Claude in chat parse this text and
// decide what to call, exactly like the original workflow.
function buildPasteFact(row) {{
  const headlineSep = /[.!?]$/.test(row.headline) ? '' : '.';
  let fact = `Contribute to ASPG (category: ${{row.category}}) entity ${{row.entityName}}: ${{row.headline}}${{headlineSep}} ${{row.detail}}`;
  if (row.pcCode !== UNDEFINED_PC) {{
    const pcName = pcNameByCode[row.pcCode] || row.pcCode;
    fact += ` (SPG profit center: ${{pcName}}, code ${{row.pcCode}})`;
  }}
  if (row.confidence !== 'asserted') fact += ` (confidence: ${{row.confidence}})`;
  if (row.isOpportunity) fact += ` (open opportunity)`;
  if (row.sourceNote) fact += ` (source: ${{row.sourceNote}})`;
  return fact;
}}

// Minimal fact text for the DIRECT tool call -- entity, confidence, and
// source_note are already their own contribute() parameters there, so
// repeating them inside the text would just be noise.
function buildDirectFact(row) {{
  const headlineSep = /[.!?]$/.test(row.headline) ? '' : '.';
  let fact = `${{row.headline}}${{headlineSep}} ${{row.detail}}`;
  if (row.pcCode !== UNDEFINED_PC) {{
    const pcName = pcNameByCode[row.pcCode] || row.pcCode;
    fact += ` (SPG profit center: ${{pcName}}, code ${{row.pcCode}})`;
  }}
  if (row.isOpportunity) fact += ` (open opportunity)`;
  return fact;
}}

function setRowStatus(card, kind, message) {{
  const n = card.dataset.index;
  const el = document.getElementById(`row-status-${{n}}`);
  el.className = 'row-status show ' + kind;
  el.textContent = message;
}}

function showBanner(kind, message) {{
  const b = document.getElementById('mcp-banner');
  b.className = 'mcp-banner show ' + (kind || '');
  b.textContent = message;
}}
function hideBanner() {{
  document.getElementById('mcp-banner').className = 'mcp-banner';
}}

// Full diagnostic dump of an McpError -- Object.getOwnPropertyNames catches
// fields plain JSON.stringify would skip on a non-enumerable Error
// property.
const DUMP_MAX = 800;
function truncateForDump(s) {{
  return s.length > DUMP_MAX ? s.slice(0, DUMP_MAX) + `...[truncated, ${{s.length}} chars total]` : s;
}}
function dumpError(err) {{
  if (!err) return 'null/undefined error';
  const lines = [];
  let props;
  try {{ props = Object.getOwnPropertyNames(err); }} catch (e) {{ props = []; }}
  for (const key of props) {{
    let val;
    try {{ val = err[key]; }} catch (e) {{ val = '<threw on read>'; }}
    let shown;
    try {{ shown = (typeof val === 'object' && val !== null) ? JSON.stringify(val) : String(val); }} catch (e) {{ shown = '<unserializable>'; }}
    lines.push(`  ${{key}}: ${{truncateForDump(shown)}}`);
  }}
  try {{ lines.push('  JSON.stringify(err): ' + truncateForDump(JSON.stringify(err))); }} catch (e) {{ lines.push('  JSON.stringify(err): <threw: ' + e.message + '>'); }}
  lines.push('  typeof err: ' + typeof err);
  lines.push('  err.constructor?.name: ' + (err && err.constructor && err.constructor.name));
  return lines.join('\\n');
}}

const PAGE_LEVEL_CODES = new Set([
  'needs_reauth', 'server_not_connected', 'selection_required', 'consent_required',
  'blocked_by_policy', 'approval_required', 'not_granted', 'capability_disabled',
  'capability_removed', 'user_changed', 'not_in_manifest'
]);
function pageLevelMessage(code) {{
  switch (code) {{
    case 'needs_reauth': return `[${{code}}] Reconnect ${{MCP_CONNECTOR_NAME}} in Settings → Connectors, then reopen this page.`;
    case 'server_not_connected': return `[${{code}}] This only works inside the Claude Desktop app, viewing this exact artifact as its owner -- not a browser tab. If you're already in Desktop, the local server/extension may not be running.`;
    case 'selection_required': return `[${{code}}] More than one matching connector is available — choose one, then reopen this page.`;
    case 'consent_required': return `[${{code}}] Allow ${{MCP_CONNECTOR_NAME}} for this page (look for a connector-permission notice, or a Claude Desktop confirmation dialog), then click Contribute again.`;
    case 'blocked_by_policy': return `[${{code}}] Your organization's policy blocks this tool from here. Use the copy-paste option below instead.`;
    case 'approval_required': return `[${{code}}] This action needs a per-call approval that isn't available on this page yet. Use the copy-paste option below instead.`;
    case 'user_changed': return `[${{code}}] The signed-in account changed — reopen this page.`;
    default: return `[${{code || 'no code'}}] One-click submit isn't available right now. Use the copy-paste option below instead.`;
  }}
}}

let mcp = null;
let mcpServerHandle = null;

async function initMcp() {{
  try {{
    mcp = (window.claude && typeof window.claude.use === 'function') ? await window.claude.use('mcp') : null;
  }} catch (e) {{ mcp = null; }}
  if (!mcp) {{
    document.getElementById('how-it-works-text').innerHTML =
      'Checked = will be contributed. Uncheck anything you\\'d rather skip, edit any wording, then press <strong>Contribute</strong> below. It builds a text block — paste it back into this same Claude chat to actually submit.';
    return;
  }}
  try {{
    mcpServerHandle = await mcp.server(MCP_HOST_SERVER);
  }} catch (err) {{
    mcpServerHandle = null;
    showBanner('warn', pageLevelMessage(err && err.code));
  }}
}}
initMcp();

// Read-only diagnostic -- reports what the mcp capability sees for both the
// plain connector name and the host: (Desktop Extension) addressing, side
// by side, so a failure can be diagnosed without devtools access. Never
// calls contribute/proposeEntity.
document.getElementById('btn-check').addEventListener('click', async () => {{
  const out = document.getElementById('output-text');
  document.getElementById('output-title').textContent = 'Connection check (read-only, nothing submitted)';
  document.getElementById('output').classList.add('show');
  const report = [];
  report.push(`window.claude present: ${{!!(window.claude && typeof window.claude.use === 'function')}}`);
  try {{
    const m = (window.claude && typeof window.claude.use === 'function') ? await window.claude.use('mcp') : null;
    report.push(`claude.use('mcp') resolved: ${{!!m}}`);
    if (m) {{
      for (const name of [MCP_CONNECTOR_NAME, MCP_HOST_SERVER]) {{
        try {{
          const info = await m.listTools(name);
          report.push(`listTools(${{name}}) => ` + JSON.stringify(info, null, 2));
        }} catch (err) {{
          report.push(`listTools(${{name}}) rejected:\\n` + dumpError(err));
        }}
      }}
      try {{
        const info = await m.listTools();
        report.push('listTools() [all servers] => ' + JSON.stringify(info.servers.map(s => ({{server: s.server, kind: s.kind, authStatus: s.authStatus, tools: s.tools.map(t => t.name)}})), null, 2));
      }} catch (err) {{
        report.push(`listTools() [all] rejected:\\n` + dumpError(err));
      }}
    }}
  }} catch (err) {{
    report.push(`claude.use('mcp') threw:\\n` + dumpError(err));
  }}
  out.value = report.join('\\n\\n');
}});

document.getElementById('btn-go').addEventListener('click', async () => {{
  const goBtn = document.getElementById('btn-go');
  const checkedCards = Array.from(document.querySelectorAll('.prop')).filter(c => c.querySelector('.cb').checked);
  if (checkedCards.length === 0) {{
    const out = document.getElementById('output-text');
    out.value = 'Nothing selected — check at least one box above.';
    document.getElementById('output').classList.add('show');
    return;
  }}

  if (!mcp || !mcpServerHandle) {{
    // Fallback: exactly the CTO's original behavior.
    const lines = [];
    const entitiesProposed = new Set();
    checkedCards.forEach(card => {{
      const row = readRow(card);
      if (row.needsNew && !entitiesProposed.has(row.entityName)) {{
        const entityType = CATEGORY_TO_ENTITY_TYPE[row.category] || 'market';
        lines.push(`Propose a new ASPG entity: ${{row.entityName}}, type ${{entityType}}.`);
        entitiesProposed.add(row.entityName);
      }}
      lines.push(buildPasteFact(row));
    }});
    document.getElementById('output-title').textContent = 'Paste this into your Claude chat';
    const out = document.getElementById('output-text');
    out.value = lines.join('\\n\\n');
    document.getElementById('output').classList.add('show');
    return;
  }}

  goBtn.disabled = true;
  goBtn.classList.add('busy');
  hideBanner();
  const entitiesProposed = new Set();
  const failedRows = [];
  const diagnostics = [];

  for (const card of checkedCards) {{
    const row = readRow(card);
    const n = card.dataset.index;
    try {{
      if (row.needsNew && !entitiesProposed.has(row.entityName)) {{
        const entityType = CATEGORY_TO_ENTITY_TYPE[row.category] || 'market';
        await mcpServerHandle[PROPOSE_ENTITY_TOOL]({{ name: row.entityName, type: entityType }});
        entitiesProposed.add(row.entityName);
      }}
      await mcpServerHandle[CONTRIBUTE_TOOL]({{
        entity: row.entityName,
        fact: buildDirectFact(row),
        confidence: row.confidence,
        source_note: row.sourceNote || '',
      }});
      card.classList.add('submitted');
      card.querySelector('.cb').disabled = true;
      setRowStatus(card, 'ok', 'Submitted to ASPG.');
    }} catch (err) {{
      const code = err && err.code;
      diagnostics.push(`=== Row ${{n}} (${{row.entityName}}) ===\\n` + dumpError(err));
      if (PAGE_LEVEL_CODES.has(code)) {{
        showBanner(code === 'blocked_by_policy' || code === 'approval_required' ? 'error' : 'warn', pageLevelMessage(code));
        failedRows.push(row);
        setRowStatus(card, 'err', 'Not submitted — see banner above.');
        card.classList.add('failed');
        continue;
      }}
      card.classList.add('failed');
      setRowStatus(card, 'err', `Couldn't submit (${{code || 'no code'}}): ${{(err && err.message) || 'unknown error'}}. Fix and click Contribute again, or copy it below.`);
      failedRows.push(row);
    }}
  }}

  goBtn.disabled = false;
  goBtn.classList.remove('busy');
  updateCount();

  if (failedRows.length > 0) {{
    document.getElementById('output-title').textContent = `${{failedRows.length}} fact(s) didn't submit — full error details below, paste-back text at the bottom`;
    const lines = failedRows.map(row => buildPasteFact(row));
    const out = document.getElementById('output-text');
    out.value = diagnostics.join('\\n\\n') + '\\n\\n--- paste this into your Claude chat instead ---\\n\\n' + lines.join('\\n\\n');
    document.getElementById('output').classList.add('show');
  }} else {{
    document.getElementById('output').classList.remove('show');
  }}
}});

document.getElementById('btn-copy').addEventListener('click', () => {{
  const out = document.getElementById('output-text');
  out.select();
  document.execCommand('copy');
  const btn = document.getElementById('btn-copy');
  btn.textContent = 'Copied';
  btn.classList.add('copied');
  setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 1500);
}});

document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvest", required=True, help="Path to the harvest JSON (see examples/sample_harvest.json)")
    parser.add_argument("--out", required=True, help="Path to write the review-page HTML")
    args = parser.parse_args()

    harvest_path = pathlib.Path(args.harvest)
    out_path = pathlib.Path(args.out)

    if not CSS_PATH.exists():
        die(f"missing stylesheet {CSS_PATH} — the plugin's assets/ dir is incomplete")

    data = load_harvest(harvest_path)
    out_path.write_text(build_html(data), encoding="utf-8")
    print(f"Wrote {out_path} ({len(data['proposals'])} proposals)")


if __name__ == "__main__":
    main()
