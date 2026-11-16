"""
Turns retrieved facts into the answer the user reads.

The agents collect facts as structured records (title, fields, table, body).
This module writes them up the way a person would answer: the answer first,
short paragraphs, a table when the data is tabular - and no SQL, table names
or other internals.  It is used whenever no language model is configured, and
as the safety net when a model call fails.

It also produces the list of sources shown under an answer.
"""
import json
import re
from typing import Any, Dict, List, Optional


Context = Dict[str, Any]

MAX_BLOCKS = 4
MAX_TABLE_ROWS = 15


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------
def format_value(value: Any) -> str:
    """Human-friendly rendering of a cell value (thousands separators, no trailing .0)."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}" if abs(value) >= 10000 else str(value)
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    text = str(value)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return format_value(float(text))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T[\d:.]+", text):
        return text.replace("T", " ")[:16]
    return text


def humanize(column: str) -> str:
    """employee_count -> Employee count"""
    words = str(column).replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else "Value"


def _pretty(value: Any) -> str:
    """Amounts stored as '389410102.00' read better as 389,410,102. Ids, dates and phone numbers are left alone."""
    text = str(value)
    if re.fullmatch(r"-?\d+\.\d{1,2}", text):
        return format_value(float(text))
    match = re.fullmatch(r"(-?\d+\.\d{2}) ([A-Z]{3})", text)   # amount with currency code
    if match:
        return f"{format_value(float(match.group(1)))} {match.group(2)}"
    return text


def _cell(text: Any) -> str:
    return _pretty(text).replace("|", "/").replace("\n", " ").strip() or "-"


def markdown_table(columns: List[str], rows: List[List[Any]]) -> str:
    shown = rows[:MAX_TABLE_ROWS]
    lines = [
        "| " + " | ".join(_cell(c) for c in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in shown:
        lines.append("| " + " | ".join(_cell(v) for v in row) + " |")
    table = "\n".join(lines)
    if len(rows) > len(shown):
        table += f"\n\n*Showing the first {len(shown)} of {len(rows)} rows.*"
    return table


# ----------------------------------------------------------------------
# Block rendering
# ----------------------------------------------------------------------
def _render_sql(ctx: Context) -> str:
    """An aggregate result: one number becomes a sentence, several rows become a table."""
    columns: List[str] = ctx.get("columns") or []
    rows: List[Dict[str, Any]] = ctx.get("rows") or []
    filters = ctx.get("filters") or ""
    scope = f" ({filters})" if filters else ""

    if not rows:
        return f"I ran the numbers and found no matching records{scope}."

    if len(rows) == 1 and len(columns) == 1:
        col, value = columns[0], rows[0].get(columns[0])
        shown = format_value(value)
        if col.lower().endswith("_count"):
            noun = col[:-6].replace("_", " ")
            plural = noun if value == 1 else (noun[:-1] + "ies" if noun.endswith("y") else noun + "s")
            verb = "is" if value == 1 else "are"
            return f"There {verb} **{shown}** {plural}{scope}."
        if col.lower() == "count":
            return f"The count is **{shown}**{scope}."
        return f"The {humanize(col).lower()} is **{shown}**{scope}."

    if len(rows) == 1:
        lines = [f"- **{humanize(c)}:** {format_value(rows[0].get(c))}" for c in columns]
        lead = f"Here are the figures{scope}:"
        return lead + "\n\n" + "\n".join(lines)

    header = [humanize(c) for c in columns]
    body = [[format_value(r.get(c)) for c in columns] for r in rows]
    lead = f"Here is the breakdown{scope}:"
    return lead + "\n\n" + markdown_table(header, body)


def _render_block(ctx: Context, with_heading: bool) -> str:
    kind = ctx.get("kind")
    if kind == "sql":
        return _render_sql(ctx)

    parts: List[str] = []
    title = ctx.get("title")
    if title:
        parts.append(f"### {title}" if with_heading else f"**{title}**")

    fields = [f for f in (ctx.get("fields") or []) if f and f[1] not in (None, "")]
    if fields:
        parts.append("\n".join(f"- **{label}:** {_pretty(value)}" for label, value in fields))

    body = ctx.get("body")
    if body:
        parts.append(str(body))

    table = ctx.get("table")
    if table and table.get("rows"):
        parts.append(markdown_table(table["columns"], table["rows"]))

    note = ctx.get("note")
    if note:
        parts.append(f"*{note}*")

    if not fields and not body and not table:
        # Unstructured passage (vector search hit or graph fact)
        text = re.sub(r"\s+", " ", str(ctx.get("text") or "")).strip()
        if text:
            parts.append(text[:420] + ("..." if len(text) > 420 else ""))

    return "\n\n".join(p for p in parts if p)


def _dedupe_versions(contexts: List[Context]) -> List[Context]:
    """Several versions of the same policy/document: keep the best match, mention the others."""
    seen: Dict[tuple, Context] = {}
    result: List[Context] = []
    for ctx in contexts:
        key = (ctx.get("kind"), ctx.get("title"))
        if ctx.get("kind") in ("policy", "document") and ctx.get("title") and key in seen:
            first = seen[key]
            version = next((v for label, v in (ctx.get("fields") or []) if label == "Version"), None)
            owner = next((v for label, v in (ctx.get("fields") or []) if label == "Owner"), None)
            if version:
                others = first.setdefault("_other_versions", [])
                others.append(f"{version}" + (f" ({owner})" if owner else ""))
            continue
        copy = dict(ctx)
        seen[key] = copy
        result.append(copy)
    for ctx in result:
        others = ctx.pop("_other_versions", None)
        if others:
            extra = "Other versions on file: " + ", ".join(others) + "."
            ctx["note"] = f"{ctx['note']} {extra}" if ctx.get("note") else extra
    return result


def compose_answer(question: str, contexts: List[Context]) -> str:
    """Write the final answer from the retrieved facts."""
    if not contexts:
        return (
            "I couldn't find anything about that in the company data you have access to. "
            "Try naming the employee, department, project, client or policy you mean."
        )

    denied = [c for c in contexts if c.get("denied")]
    allowed = [c for c in contexts if not c.get("denied")]

    if not allowed:
        reasons = list(dict.fromkeys(c.get("body") or str(c.get("text", "")).replace("Access denied: ", "") for c in denied))
        return "I can't share that with you. " + " ".join(r if r.endswith(".") else r + "." for r in reasons[:2])

    # Structured facts first, loose passages after
    structured = [c for c in allowed if c.get("kind")]
    passages = [c for c in allowed if not c.get("kind")]
    ordered = _dedupe_versions(structured) + passages[: max(0, 2 if structured else MAX_BLOCKS)]
    blocks = ordered[:MAX_BLOCKS]

    # Title-only matches all carry the same "you cannot open this" note: say it once, at the end
    restricted_notes = list(dict.fromkeys(c["note"] for c in blocks if c.get("restricted") and c.get("note")))
    if restricted_notes:
        blocks = [({**c, "note": None} if c.get("restricted") else c) for c in blocks]

    multiple = len(blocks) > 1
    rendered = [_render_block(c, with_heading=multiple and c.get("kind") != "sql") for c in blocks]
    rendered = [r for r in rendered if r]

    pieces: List[str] = []
    if multiple and not any(c.get("kind") == "sql" for c in blocks):
        pieces.append("Here's what I found.")
    elif not multiple and passages and not structured:
        pieces.append("Here is the most relevant passage I found:")
    pieces.extend(rendered)

    if len(ordered) > len(blocks):
        pieces.append(f"*There are {len(ordered) - len(blocks)} more matches. Ask a more specific question to narrow it down.*")

    if restricted_notes:
        restricted_count = sum(1 for c in blocks if c.get("restricted"))
        if restricted_count > 1:
            pieces.append(
                "*These are listed by title only. To read a document, request access to it in the Knowledge Explorer "
                "or the Operations Center; a system administrator decides.*"
            )
        else:
            pieces.append(f"*{restricted_notes[0]}*")

    if denied:
        reasons = list(dict.fromkeys(c.get("body") or str(c.get("text", "")) for c in denied))
        pieces.append("**Not shown:** " + " ".join(r if r.endswith(".") else r + "." for r in reasons[:2]))

    return "\n\n".join(pieces)


# ----------------------------------------------------------------------
# Sources shown under an answer
# ----------------------------------------------------------------------
def _friendly_label(ctx: Context) -> str:
    if ctx.get("label"):
        return str(ctx["label"])
    source = str(ctx.get("source") or "Company data")
    match = re.match(r"Qdrant:\s*(\w+)\s*-\s*'(.*)'", source)
    if match:
        collection = {"documents": "Document", "policies": "Policy", "emails": "Email", "meetings": "Meeting", "chats": "Past chat"}.get(match.group(1), match.group(1).title())
        return f"{collection}: {match.group(2)}"
    if source.startswith("Neo4j"):
        return "Organisation graph"
    return re.sub(r"^PostgreSQL:\s*", "", source)


def _store(ctx: Context) -> str:
    source = str(ctx.get("source") or "")
    if source.startswith("Qdrant"):
        return "documents"
    if source.startswith("Neo4j"):
        return "graph"
    return "database"


def build_sources(contexts: List[Context]) -> List[Dict[str, str]]:
    """Unique, readable source list for the UI. Denied lookups are not sources."""
    sources: List[Dict[str, str]] = []
    seen = set()
    for ctx in contexts or []:
        if ctx.get("denied") or ctx.get("no_source"):
            continue
        label = _friendly_label(ctx)
        if label in seen:
            continue
        seen.add(label)
        sources.append({"label": label[:120], "type": _store(ctx)})
    return sources[:8]


def context_for_prompt(contexts: List[Context]) -> str:
    """Numbered, plainly labelled facts for a language model - without SQL text."""
    lines = []
    for idx, ctx in enumerate(contexts, start=1):
        label = _friendly_label(ctx)
        if ctx.get("kind") == "sql":
            rows = json.dumps(ctx.get("rows") or [], default=str)[:3000]
            filters = f" Filters applied: {ctx.get('filters')}." if ctx.get("filters") else ""
            lines.append(f"[{idx}] {label}\nResult rows: {rows}.{filters}")
        else:
            lines.append(f"[{idx}] {label}\n{ctx.get('text')}")
    return "\n\n".join(lines)
