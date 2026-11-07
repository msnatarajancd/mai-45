#!/usr/bin/env python3
"""Build the demonstrator's Markdown and PDF from the checked synthetic fixtures.

Run from the repository root: .venv/bin/python scripts/build_recovery_demo_guide.py
The PDF requires reportlab; --markdown-only needs only application dependencies.
This script never opens or clears the user's result or accepted-case databases.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
from html import escape
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "recovery/progress/data"
DEFAULT_MD = ROOT / "docs/RECOVERY_PROGRESS_DEMO_GUIDE.md"
DEFAULT_PDF = ROOT / "output/pdf/ReadyRelief_Recovery_Progress_Demo_Guide.pdf"
PROOF = ROOT / ".local/synthetic-expansion/document"
SPECIALISTS = ("housing", "utilities", "insurance", "rebuild")
NAMES = {"housing": "Housing", "utilities": "Utilities", "insurance": "Insurance & funding", "rebuild": "Rebuild"}
SHORT = {"housing": "H", "utilities": "U", "insurance": "I", "rebuild": "R"}
COLORS = {"red": "#AA332B", "yellow": "#946500", "green": "#22724D", "unknown": "#5C6572", "not_applicable": "#5C6572", None: "#5C6572"}


def clean(value):
    """Use supported punctuation and ASCII hyphens with standard PDF fonts."""
    text = str(value)
    for original, replacement in {"\u2013": "-", "\u2014": "-", "\u2011": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2192": "->", "\u2022": "-"}.items():
        text = text.replace(original, replacement)
    return text


def money(value):
    return "unknown" if value is None else f"${Decimal(value):,.0f}" if Decimal(value) == Decimal(value).to_integral() else f"${Decimal(value):,.2f}"


def fact_money(fact):
    if fact is None:
        return "unknown"
    return money(fact.amount) if fact.currency == "USD" else f"{fact.currency} {money(fact.amount)[1:]}"


def yn(value):
    return "unknown" if value is None else "yes" if value else "no"


def state_label(state):
    return "Paused" if state is None else state.replace("_", " ").title()


def id_span(rows):
    ids = [row["id"] for row in rows]
    return f"{ids[0]} through {ids[-1]} ({len(ids)})"


def load_verified():
    """Check authored expectations without fabricating routine results for danger.

    Configured MCP service errors use the orchestrator's failure result, not a
    successful domain evaluation. Root runtime tests additionally exercise stdio.
    """
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    from recovery.progress.utilities import check_utilities
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.rebuild import check_rebuild
    from recovery.progress.orchestrator import _failed_result
    from recovery.progress.priorities import select_next_actions

    catalogs = {name: json.loads((DATA / f"{name}.json").read_text()) for name in ("scenarios", "housing", "providers", "checklists", "demo_scenarios")}
    required_counts = {"scenarios": 24, "housing": 48, "providers": 60, "checklists": 8, "demo_scenarios": 24}
    for name, count in required_counts.items():
        if len(catalogs[name]) != count:
            raise ValueError(f"{name}: expected {count}, found {len(catalogs[name])}")
    metadata = {row["id"]: row for row in catalogs["demo_scenarios"]}
    if set(metadata) != {row["id"] for row in catalogs["scenarios"]}:
        raise ValueError("Scenario metadata IDs must exactly match story IDs")
    functions = dict(zip(SPECIALISTS, (check_housing, check_utilities, check_insurance_and_funding, check_rebuild)))
    checked = []
    for story in catalogs["scenarios"]:
        meta = metadata[story["id"]]
        expect = {row["id"]: row for row in meta["checkpoints"]}
        if [c["id"] for c in story["checkpoints"]] != ["initial", "update", "later"] or set(expect) != {"initial", "update", "later"}:
            raise ValueError(f"Unexpected checkpoint structure: {story['id']}")
        entry = {"story": story, "metadata": meta, "checkpoints": []}
        for raw in story["checkpoints"]:
            inputs = load_scenario(story["id"], raw["id"])
            expected = expect[raw["id"]]
            paused = inputs.immediate_danger is not False
            if paused:
                signals = {key: None for key in SPECIALISTS}
                execution = {key: "paused" for key in SPECIALISTS}
                results, actions = [], []
            else:
                results = [(_failed_result(key, inputs) if key in inputs.specialist_failures else function(inputs, now=inputs.as_of)) for key, function in functions.items()]
                signals = {result.specialist: result.state.value for result in results}
                execution = {result.specialist: result.execution_state.value for result in results}
                actions = list(select_next_actions(inputs, tuple(results)))
            primary = actions[0].key if actions else None
            for field, actual in (("expected_signals", signals), ("expected_execution", execution), ("expected_primary_action", primary)):
                if expected[field] != actual:
                    raise ValueError(f"{story['id']}/{raw['id']} {field}: authored {expected[field]!r}, actual {actual!r}")
            entry["checkpoints"].append({"id": raw["id"], "raw": raw, "inputs": inputs, "expected": expected,
                "paused": paused, "signals": signals, "execution": execution, "results": results,
                "primary_key": primary, "primary_title": actions[0].title if actions else ("Routine checks paused" if paused else "No next action"),
                "primary_reason": actions[0].reason if actions else "", "actions": actions})
        checked.append(entry)
    return catalogs, checked


def household_facts(entry):
    h = entry["checkpoints"][0]["inputs"].household
    adults = f"{h.adults if h.adults is not None else '?'} {'adult' if h.adults == 1 else 'adults'}"
    children = f"{h.children if h.children is not None else '?'} {'child' if h.children == 1 else 'children'}"
    people = "Household size unconfirmed" if h.total is None else f"{h.total} {'person' if h.total == 1 else 'people'} ({adults}, {children})"
    return clean(f"{people}; {h.county or 'county unknown'}, {h.area or 'area unknown'}. Housing budget {money(h.housing_budget)}/night; accessibility {yn(h.accessibility)}, pets {yn(h.pets)}, vehicle {yn(h.has_vehicle)}. Contribution: {h.contribution_band or 'not supplied'}.")


def checkpoint_facts(cp):
    inputs = cp["inputs"]
    funding = inputs.funding
    fragments = [f"Accommodation: {inputs.accommodation_status}"]
    evidence = Counter(e.status for e in inputs.evidence)
    fragments.append("Evidence: " + (", ".join(f"{n} {state.replace('_', ' ')}" for state, n in sorted(evidence.items())) or "none linked"))
    insurance = next((result for result in cp["results"] if result.specialist == "insurance"), None)
    fund = next((item for item in insurance.items if item.id == "funding"), None) if insurance else None
    if fund:
        gap = fund.fields["Exact stage gap"].replace("USD ", "$")
        fragments.append(f"Stage gap: {gap.lower() if gap == 'Unknown' else gap}")
    fragments.append("Stage cost / allocation: " + " / ".join(fact_money(f) for f in (funding.estimated_cost, funding.exact_allocation)))
    if funding.spent_from_allocation:
        fragments.append("Spent: " + fact_money(funding.spent_from_allocation))
    payments = [f"{label} {fact_money(getattr(funding, key))}" for label, key in (("expected", "expected_payment"), ("approved", "approved_payment"), ("received", "received_payment")) if getattr(funding, key)]
    if payments:
        fragments.append("Payment: " + ", ".join(payments))
    return clean(". ".join(fragments) + ".")


def insurance_parts(cp):
    insurance = next((r for r in cp["results"] if r.specialist == "insurance"), None)
    if insurance is None or insurance.execution_state.value == "failed":
        return ""
    labels = {"preparation": "prep", "funding": "funds", "insurance-payment": "payment"}
    return "; ".join(f"{labels[item.id]} {state_label(item.state.value)}" for item in insurance.items if item.id in labels)


def execution_note(cp):
    if cp["paused"]:
        return "Paused: no routine check or primary action is produced."
    special = [f"{SHORT[key]} {value.replace('_', ' ')}" for key, value in cp["execution"].items() if value != "complete"]
    return "Execution: " + ("; ".join(special) + "; remaining checks complete." if special else "all four checks complete.")


def compact_facts(cp):
    inputs = cp["inputs"]
    funding = inputs.funding
    evidence = Counter(e.status for e in inputs.evidence)
    text = f"Stay: {inputs.accommodation_status}. Evidence: " + (", ".join(f"{n} {status.replace('_', ' ')}" for status, n in sorted(evidence.items())) or "none linked") + "."
    text += " Cost " + fact_money(funding.estimated_cost)
    text += "; allocation " + fact_money(funding.exact_allocation) + "."
    if funding.spent_from_allocation:
        text += " Spent " + fact_money(funding.spent_from_allocation) + "."
    insurance = next((r for r in cp["results"] if r.specialist == "insurance"), None)
    fund = next((item for item in insurance.items if item.id == "funding"), None) if insurance else None
    if fund:
        text += " Gap " + fund.fields["Exact stage gap"].replace("USD ", "$").lower() + "."
    for label, attr in (("Expected", "expected_payment"), ("Approved", "approved_payment"), ("Received", "received_payment")):
        fact = getattr(funding, attr)
        if fact:
            text += f" {label} {fact_money(fact)}."
    return text


def front_sections(catalogs, entries):
    """Shared authoring blocks keep the Markdown and PDF statements aligned."""
    return [
        ("Start the demo", [
            ("lead", "Recovery Progress / Demonstrator's guide"),
            ("p", "24 fictional households. 72 authored checkpoints. Four specialist views and one ranked next step. Use this guide to show why a result changes, what remains unknown, and what the prototype does with those facts."),
            ("h", "Open the preview"),
            ("code", "python -m streamlit run app.py"),
            ("numbered", ["Use the interpreter where requirements.txt is installed (for example .venv/bin/python). In the app navigation, open Recover > Recovery Progress · Preview.", "Expand Choose story or saved case. Set Dashboard source to Synthetic stories. Choose Household story and Story checkpoint.", "The checkpoint labels are 1 · Starting point (initial), 2 · An update (update), and 3 · Later in recovery (later). Select Refresh checks after each change.", "Wait for Last run activity and the four specialist cards. Read One manageable next step, open relevant View details, then compare Your two recovery tracks."]),
            ("h", "Say this before showing results"),
            ("p", "All identities, addresses, prices, capacities, ratings, observations, provider responses and timing are fictional. Local deterministic checks run through LangGraph and the actual MCP stdio boundary. This demo does not reserve space, send enquiries, approve claims or dispatch work."),
            ("h", "Reading the signals"),
            ("table", [["Signal", "Meaning"], ["Red", "Action needed for the named condition"], ["Yellow", "In progress"], ["Green", "Condition met for the named check"], ["Unknown", "Missing, stale or unavailable information"], ["Not applicable", "A separate status, not success or failure"]]),
            ("note", "Execution and condition are different. Complete + Red means the check ran and found a problem. Needs information or Couldn't update appears gray. Green does not certify home safety or insurer approval.")
        ]),
        ("Choose a demo route", [
            ("h", "Five minutes: the main recovery story"),
            ("table", [["Time", "Presenter action", "Point to make"], ["0:00-1:00", "Rivera / initial > Refresh checks", "Show the source badge, four cards and primary action. Open housing details to compare rooms with spaces."], ["1:00-2:30", "Rivera / update > Refresh checks", "Read What changed and compare the Home & daily life and Costs & funding tracks."], ["2:30-4:00", "Chen / later > Refresh checks", "Repairs and return home do not establish reimbursement receipt. Inspect preparation, funding and payment separately."], ["4:00-5:00", "Open Timing & assumptions", "Illustrative story ranges are not forecasts. End with the next action and the evidence behind it."]]),
            ("h", "Fifteen minutes: dependencies and uncertainty"),
            ("numbered", ["Minutes 0-5: follow the five-minute route. Use the scenario pages to read exact card states and action text.", "Minutes 5-8: Alvarez initial > update > later. Compare exact stage cost, explicit allocation and the remaining gap with provider quotes and work commitments.", "Minutes 8-10: Baptiste initial > update. Show accessibility, household suitability, pets, transport and availability as separate housing constraints.", "Minutes 10-12: Morgan initial > later. Insurance can be not applicable while household funding still needs information. Completed repairs remain distinct from funding certainty.", "Minutes 12-14: Campbell initial > update > later. Read Couldn't update / No new observation at update and the partial recommendation from the remaining checks. Show the fresh utility result at later.", "Minutes 14-15: Williams initial. Refresh checks is disabled until immediate safety is explicitly assessed; missing facts are not filled from another household."]),
            ("h", "Technical route: fifteen additional minutes"),
            ("numbered", ["List the five MCP tools and invoke the compact scenario payload examples on the next page.", "Compare assess_insurance_readiness and assess_funding_gap for the same checkpoint: both expose the same shared preparation/funding result.", "Inspect source_mode, context_key and input_fingerprint. Explain how context changes make earlier snapshots historical.", "Record a simulated provider update, refresh, then switch checkpoints to show the override is scoped to one story checkpoint.", "Use the fixture and metadata files in the catalog reference to trace a displayed condition to exact source facts."]),
            ("note", "For a rehearsed baseline, use a fresh demo-only progress database path at launch. Do not clear the existing progress database or the accepted recovery-case database.")
        ]),
        ("Demonstrate the five MCP tools", [
            ("p", "Run the server from this repository with the installed interpreter. It uses local stdio; no API key or external provider integration is required."),
            ("code", ".venv/bin/python -m recovery.progress.mcp_server"),
            ("p", "In a compatible MCP host, configure the interpreter as command, [-m, recovery.progress.mcp_server] as args, and the repository as cwd (or set PYTHONPATH to its absolute path). Call each tool using the arguments below."),
            ("tool", ("find_temporary_housing", {"scenario_id": "baptiste", "checkpoint_id": "initial"}, "Compare needs, room/space units, budget and suitability; no booking.")),
            ("tool", ("check_utility_health", {"scenario_id": "rivera", "checkpoint_id": "initial"}, "Read address scope, observation age, electricity, water supply, potability and gas applicability.")),
            ("tool", ("assess_insurance_readiness", {"scenario_id": "chen", "checkpoint_id": "later"}, "Inspect preparation, stage funding and decision/receipt as separate result items.")),
            ("tool", ("assess_funding_gap", {"scenario_id": "alvarez", "checkpoint_id": "initial"}, "Explain a gap using current exact same-stage USD cost and explicit allocation.")),
            ("tool", ("search_repair_providers", {"scenario_id": "alvarez", "checkpoint_id": "update"}, "Read trade/area matches, catalog availability, simulated interaction and quote; no contact.")),
            ("h", "Response and context contract"),
            ("p", "Successful responses contain source_mode, context_key, input_fingerprint and result. The result includes state, execution_state, items, missing facts and action candidates. The graph uses four specialist calls (insurance already includes funding), then selects up to three next actions."),
            ("p", "Use either scenario_id/checkpoint_id or a complete typed payload. The app supplies payload when it has saved-case facts or simulated overrides; never pass both mechanisms. A scenario-only tool call uses fixture baseline data and does not read dashboard interaction overrides."),
            ("p", "Repeat the fixture sanity check through the real MCP boundary with this repository command (it validates synthetic expectations, not live availability):"),
            ("code", "python -m scripts.verify_recovery_demo_data \\\n  --output artifacts/recovery-demo-data-verification.json"),
            ("note", "Safety-unknown or danger checkpoints reject routine MCP calls. A configured service failure returns a tool error; the graph shows Couldn't update with no new observation and excludes that specialist's old actions.")
        ]),
        ("Synthetic data catalog", [
            ("p", "The guide is generated from the JSON fixtures and checked against the authored demo expectations. Story ordering and existing IDs are retained. Catalog selections and overrides apply only to their checkpoint."),
            ("table", [["File / count", "Fields and coverage"], ["scenarios.json / 24 stories, 72 checkpoints", "Household size, adults/children, fictional location, access/pets/transport, nightly budget, contribution band, safety, accommodation, utilities, evidence, funding, trades and interactions."], ["housing.json / 48 sites", "Four categories: hotel, church, school, official shelter. Rooms vs spaces, occupancy, capacity, activation, household togetherness, accessibility, pets, price, distance and transport."], ["providers.json / 60 providers", "Five trades: Electrician, Contractor, Plumber, Roofer, Pool specialist. County/areas, fictional rating/review count, availability and accessible service."], ["checklists.json / 8 profiles", "Neutral fictional requirements with explicit evidence links. No real insurer policy or approval rules."], ["demo_scenarios.json / 24 presenter records", "Theme, presenter goal, key lesson, recommended tool, checkpoint talk track, expected four signals/execution states and primary action key."]]),
            ("h", "Stable IDs"),
            ("p", "Housing: " + "; ".join(f"{category}: " + id_span([row for row in catalogs["housing"] if row["category"] == category]) for category in dict.fromkeys(row["category"] for row in catalogs["housing"])) + "."),
            ("p", "Providers: " + "; ".join(f"{trade}: " + id_span([row for row in catalogs["providers"] if row["trade"] == trade]) for trade in dict.fromkeys(row["trade"] for row in catalogs["providers"])) + "."),
            ("p", "Checklists: " + "; ".join(f"{row['id']} ({row['label']}: {row['description']})" for row in catalogs["checklists"]) + "."),
            ("note", "Checkpoint catalog controls: housing_ids/provider_ids select known records; an empty list selects none. housing_overrides/provider_overrides alter allowed fields on selected records. *_age_hours and *_validity_hours control freshness. IDs and synthetic provenance cannot be overwritten.")
        ]),
        ("Interactions, history and safe rehearsal", [
            ("h", "Record a simulated provider response"),
            ("numbered", ["Choose Synthetic stories > Alvarez > 1 · Starting point, then Refresh checks. Expand View details · Rebuild my life.", "Find Demo Bay Contractor (contractor-1); if the saved checkpoint already has a different interaction, use the next allowed event shown or start with a new demo-only progress database.", "In Simulated update choose an offered event, then select Record simulated update. The app says the update was recorded and asks for Refresh checks.", "Refresh checks. Inspect the Interaction field and next step. The supported forward chain is shortlisted > enquiry recorded > awaiting reply > quote received > quote accepted > work committed; decline is offered at awaiting reply or quote received.", "The control changes only interaction state. It does not invent a monetary quote, send a message or complete repairs. Work committed remains distinct from repairs reported complete.", "Switch to a different Story checkpoint. Refresh manually. Its authored interactions and separately stored overrides apply; a change at initial does not edit update or later."]),
            ("h", "Resume without deleting data"),
            ("p", "Reloading does not start checks. The latest attempt survives reload; an abandoned in-flight attempt becomes interrupted and needs Refresh checks. After an input, checkpoint or source change, earlier results are historical and current recommendations stay hidden until a successful refresh."),
            ("p", "What changed compares the latest stored snapshot for that household context with the new one. Present initial > update > later for chronological narration. Jumping backwards is a comparison with a different authored checkpoint, not real recovery history."),
            ("p", "After a specialist fails, Earlier successful observation - outdated is available only if a prior successful result exists for the same household context, source and checkpoint. It retains its original timestamp and never supplies a current recommendation. Campbell initial > update crosses checkpoints, so that sequence does not show the initial observation inside the failed update's details."),
            ("code", "READYRELIEF_PROGRESS_DB_PATH=.local/recovery-demo-session-01.sqlite3 \\\n  .venv/bin/python -m streamlit run app.py"),
            ("p", "Choose a new, unused filename for each clean rehearsal. This changes only the preview result store. Do not remove the existing database. Saved recovery case remains a separate source, with user-reported facts and unsupported availability, exact funding and timing left unknown."),
            ("h", "Claims to avoid"),
            ("p", "Capacity is a synthetic observation, not a reservation. Water supply does not prove drinking-water safety; an area report does not prove address restoration. Saved evidence does not prove insurer acceptance. Expected or approved payment is not received money, and received-but-unallocated money is not available stage allocation. A quote is not accepted, scheduled or completed work."),
            ("note", "Source references: docs/RECOVERY_PROGRESS.md; ui/recovery_progress_page.py and ui/recovery_progress_components.py; recovery/progress/{fixtures,models,mcp_server,orchestrator,priorities}.py; recovery/progress/data/*.json. All scenario names and catalog labels in this guide are synthetic.")
        ]),
        ("Story index and presenter cues", [
            ("p", "Choose the exact household label in Household story. The ID is the scenario_id for MCP calls. Each story has initial, update and later. H / U / I / R on the following pages means Housing / Utilities / Insurance & funding / Rebuild."),
            ("table", [["Household / ID", "Theme", "Presenter cue"]] + [[entry["story"]["label"] + " / " + entry["story"]["id"], entry["metadata"]["theme"], entry["metadata"]["key_lesson"]] for entry in entries]),
            ("note", "Expected states assume fixture baseline data with no dashboard interaction overrides. Insurance & funding is the combined card; sub-signals list preparation/funding/payment. Paused checkpoints produce no routine result or primary action. $ means USD; other currencies are labeled. Cost/allocation are authored totals; a gap requires current same-stage USD facts. Evidence counts summarize supplied records, not insurer verification.")
        ]),
    ]


def markdown(catalogs, entries, sections):
    parts = ["# ReadyRelief Recovery Progress demo guide", "", "Generated from the synthetic fixtures on 2026-11-06. Rebuild with `.venv/bin/python scripts/build_recovery_demo_guide.py`. PDF generation requires `reportlab`; use `--markdown-only` to generate Markdown with the application dependencies alone.", ""]
    for title, blocks in sections:
        parts += [f"## {title}", ""]
        for kind, content in blocks:
            if kind in ("p", "lead", "note"):
                parts += [content, ""]
            elif kind == "h":
                parts += [f"### {content}", ""]
            elif kind == "code":
                parts += ["```bash", content, "```", ""]
            elif kind == "numbered":
                parts += [f"{i}. {value}" for i, value in enumerate(content, 1)] + [""]
            elif kind == "table":
                parts += ["| " + " | ".join(clean(value).replace("|", "\\|") for value in row) + " |" for row in [content[0], ["---"] * len(content[0]), *content[1:]]] + [""]
            elif kind == "tool":
                name, payload, explanation = content
                parts += [f"### `{name}`", "", "```json", json.dumps(payload), "```", "", explanation, ""]
    parts += ["## The 24 stories and their expected checkpoints", "", "$ means USD; other currencies are labeled. Stage cost/allocation are the authored totals; exact gap uses current matching facts after recorded spend. Evidence counts summarize supplied records; only explicit requirement links drive readiness. Execution status is listed independently of signal color.", ""]
    for n, entry in enumerate(entries, 1):
        story, meta = entry["story"], entry["metadata"]
        parts += [f"### {n:02d}. {story['label']} (`{story['id']}`)", "", f"**Theme:** {clean(meta['theme'])}", "", household_facts(entry), "", f"**Presenter goal:** {clean(meta['presenter_goal'])}", "", f"**Key lesson:** {clean(meta['key_lesson'])}", "", f"**Recommended MCP tool:** `{meta['recommended_tool']}`", "", "| Checkpoint | Housing | Utilities | Insurance & funding | Rebuild | Primary action |", "| --- | --- | --- | --- | --- | --- |"]
        for cp in entry["checkpoints"]:
            parts.append("| " + " | ".join([cp["id"], *[state_label(cp["signals"][s]) for s in SPECIALISTS], clean(cp["primary_title"])]) + " |")
        parts.append("")
        for cp in entry["checkpoints"]:
            parts += [f"**{cp['id']} - {cp['inputs'].as_of.date().isoformat()}:** {checkpoint_facts(cp)}", "", execution_note(cp) + (" Insurance detail: " + insurance_parts(cp) + "." if insurance_parts(cp) else ""), "", f"Presenter: {clean(cp['expected']['talk_track'])}", ""]
            if cp["primary_key"]:
                parts += [f"Primary action key: `{cp['primary_key']}`. {clean(cp['primary_reason'])}", ""]
    return "\n".join(parts)


def write_pdf(path, sections, entries):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

    ink, muted, accent, paper = "#17313B", "#51616A", "#0C6E6E", "#F1F6F6"
    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=colors.HexColor(ink), spaceAfter=14),
        "lead": ParagraphStyle("lead", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor(accent), spaceAfter=11),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor(ink), spaceBefore=10, spaceAfter=5),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.1, leading=12.6, textColor=colors.HexColor(ink), spaceAfter=7),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.2, leading=10.8, textColor=colors.HexColor(ink), spaceAfter=5),
        "tiny": ParagraphStyle("tiny", fontName="Helvetica", fontSize=7.8, leading=10, textColor=colors.HexColor(ink), spaceAfter=3),
        "note": ParagraphStyle("note", fontName="Helvetica", fontSize=8.3, leading=11.4, textColor=colors.HexColor(muted), backColor=colors.HexColor(paper), borderPadding=8, spaceBefore=5, spaceAfter=8),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8, leading=11, textColor=colors.HexColor(ink), backColor=colors.HexColor(paper), borderPadding=7, spaceBefore=5, spaceAfter=9, wordWrap="CJK"),
        "story": ParagraphStyle("story", fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=colors.HexColor(ink), spaceAfter=4),
        "theme": ParagraphStyle("theme", fontName="Helvetica-Bold", fontSize=8.8, leading=11.5, textColor=colors.HexColor(accent), spaceAfter=4),
    }

    def para(text, style="p", raw=False):
        return Paragraph(text if raw else escape(clean(text)).replace("\n", "<br/>"), styles[style])

    def table(rows, widths=None, style="small"):
        grid = [[para(value, style) for value in row] for row in rows]
        obj = Table(grid, colWidths=widths, hAlign="LEFT", repeatRows=1)
        obj.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(paper)), ("LINEBELOW", (0, 0), (-1, 0), .7, colors.HexColor(accent)), ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#D8E2E3")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        return obj

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CDDCDD"))
        canvas.line(42, 39, 570, 39)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(muted))
        canvas.drawString(42, 26, "READYRELIEF / RECOVERY PROGRESS / SYNTHETIC DEMO")
        canvas.drawRightString(570, 26, str(doc.page))
        canvas.restoreState()

    path.parent.mkdir(parents=True, exist_ok=True)
    document = BaseDocTemplate(str(path), pagesize=letter, title="ReadyRelief Recovery Progress Demo Guide", author="ReadyRelief", leftMargin=42, rightMargin=42, topMargin=40, bottomMargin=51)
    document.addPageTemplates(PageTemplate(id="guide", frames=Frame(42, 51, 528, 701, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0), onPage=footer))
    flow = []
    for index, (title, blocks) in enumerate(sections):
        if index:
            flow.append(PageBreak())
        flow.append(para(title, "title"))
        for kind, content in blocks:
            if kind in ("p", "lead", "h", "note", "code"):
                flow.append(para(content, kind))
            elif kind == "numbered":
                for n, value in enumerate(content, 1):
                    flow.append(para(f"{n}. {value}", "p"))
            elif kind == "table":
                widths = ([80, 180, 268] if index == 1 else [105, 423]) if len(content[0]) == 2 else [80, 180, 268]
                if index == 5:
                    content = [["Stories 01-12", "Stories 13-24"]] + [[content[n + 1][0] + "\n" + content[n + 1][1], content[n + 13][0] + "\n" + content[n + 13][1]] for n in range(12)]
                    widths = [264, 264]
                flow.append(table(content, widths=widths, style="tiny" if index == 5 else "small"))
                flow.append(Spacer(1, 6))
            elif kind == "tool":
                name, payload, explanation = content
                flow.append(para(name, "h"))
                flow.append(para(json.dumps(payload), "code"))
                flow.append(para(explanation, "small"))

    for index, entry in enumerate(entries):
        if index % 2 == 0:
            flow.append(PageBreak())
            flow.append(para(f"Story walkthroughs / {index + 1:02d}-{index + 2:02d}", "h"))
        else:
            flow.append(Spacer(1, 14))
        story, meta = entry["story"], entry["metadata"]
        card = [para(f"{index + 1:02d}. {story['label']} / {story['id']}", "story"), para(meta["theme"], "theme"), para(household_facts(entry), "tiny"), para("Show: " + meta["presenter_goal"], "tiny")]
        rows = [[para("Checkpoint / key facts", "tiny"), para("Four signals", "tiny"), para("Primary action / presenter cue", "tiny")]]
        for cp in entry["checkpoints"]:
            facts = f"<b>{escape(cp['id'])} / {cp['inputs'].as_of.date().isoformat()}</b><br/>" + escape(compact_facts(cp))
            signal_text = "<br/>".join(" / ".join(f'<font color="{COLORS[cp["signals"][key]]}"><b>{SHORT[key]} {state_label(cp["signals"][key])}</b></font>' for key in pair) for pair in (("housing", "utilities"), ("insurance", "rebuild")))
            signal_text += "<br/>" + escape(execution_note(cp).replace("Execution: ", "").replace("all four checks complete.", "All complete.").replace("remaining checks complete.", "others complete."))
            if insurance_parts(cp):
                signal_text += "<br/><i>" + escape(insurance_parts(cp)) + "</i>"
            action = f"<b>{escape(clean(cp['primary_title']))}</b><br/>" + escape(clean(cp["expected"]["talk_track"]))
            rows.append([para(facts, "tiny", raw=True), para(signal_text, "tiny", raw=True), para(action, "tiny", raw=True)])
        grid = Table(rows, colWidths=[181, 126, 221], hAlign="LEFT")
        grid.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(paper)), ("LINEBELOW", (0, 0), (-1, 0), .7, colors.HexColor(accent)), ("LINEBELOW", (0, 1), (-1, -1), .25, colors.HexColor("#D8E2E3")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        card += [grid, Spacer(1, 5), para("Lesson: " + meta["key_lesson"] + " | MCP: " + meta["recommended_tool"], "tiny")]
        flow.append(KeepTogether(card))
    document.build(flow)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--markdown-only", action="store_true")
    args = parser.parse_args()
    catalogs, entries = load_verified()
    sections = front_sections(catalogs, entries)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown(catalogs, entries, sections), encoding="utf-8")
    if not args.markdown_only:
        write_pdf(args.pdf, sections, entries)
    PROOF.mkdir(parents=True, exist_ok=True)
    proof = [{"id": entry["story"]["id"], "checkpoints": [{"id": cp["id"], "signals": cp["signals"], "execution": cp["execution"], "primary_key": cp["primary_key"], "primary_title": cp["primary_title"]} for cp in entry["checkpoints"]]} for entry in entries]
    (PROOF / "guide-validation.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Verified {len(entries)} stories and {sum(len(e['checkpoints']) for e in entries)} checkpoint expectations.")
    print(args.markdown)
    if not args.markdown_only:
        print(args.pdf)


if __name__ == "__main__":
    main()
