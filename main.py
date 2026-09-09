"""
Evaluate how well Explore_Ontology surfaces relevant MathModDB
schema elements for natural-language researcher questions.

Only Explore_Ontology is available for retrieval. For each benchmark
case in cases.json, the run requests classes, object properties, data
properties, and qualifier properties. Returned Q/P IDs are scored
against the reference set.

Cases live in cases.json with structure:

    {
      "<query string>": {
        "name": "<short slug>",
        "classes":           [{"id": "...", "label": "..."}, ...],
        "object_properties": [...],
        "data_properties":   [...],
        "qualifiers":        [...]
      },
      ...
    }

Metric: recall of the returned ID set against the reference ID set.

Run with:
    python main.py
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

load_dotenv()
console = Console()
client = anthropic.Anthropic()

MCP_URL = os.environ.get(
    "MATHMODDB_MCP_URL",
    "https://9f0bd004-46b8-403b-9f67-30d65c0a01de.ma.bw-cloud-instance.org/mathmoddb/mcp",
)
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 8000
CASES_PATH = Path(os.environ.get("CASES_PATH", "cases.json"))


# ---------- case schema -------------------------------------------------


class CaseEntry(BaseModel):
    id: str
    label: str


class CaseDefinition(BaseModel):
    name: str
    theme: str = ""
    classes: list[CaseEntry] = Field(default_factory=list)
    object_properties: list[CaseEntry] = Field(default_factory=list)
    data_properties: list[CaseEntry] = Field(default_factory=list)
    qualifiers: list[CaseEntry] = Field(default_factory=list)

    def all_ids(self) -> set[str]:
        return (
            {e.id for e in self.classes}
            | {e.id for e in self.object_properties}
            | {e.id for e in self.data_properties}
            | {e.id for e in self.qualifiers}
        )

    def label_lookup(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for group in (
            self.classes,
            self.object_properties,
            self.data_properties,
            self.qualifiers,
        ):
            for e in group:
                out[e.id] = e.label
        return out


def load_cases(path: Path) -> dict[str, CaseDefinition]:
    """Returns a dict mapping query string -> CaseDefinition."""
    raw = json.loads(path.read_text())
    return {query: CaseDefinition.model_validate(payload) for query, payload in raw.items()}


# ---------- response schema --------------------------------------------


class Scaffold(BaseModel):
    classes: list[str] = Field(default_factory=list)
    object_properties: list[str] = Field(default_factory=list)
    data_properties: list[str] = Field(default_factory=list)
    qualifier_properties: list[str] = Field(default_factory=list)

    def all_ids(self) -> set[str]:
        return (
            set(self.classes)
            | set(self.object_properties)
            | set(self.data_properties)
            | set(self.qualifier_properties)
        )


# ---------- prompts ----------------------------------------------------


SYSTEM_PROMPT = (
    "You are answering a researcher's question about the MathModDB "
    "Wikibase schema. Your job is SCHEMA discovery, not instance "
    "retrieval: you return classes and properties (Q/P codes that "
    "describe a kind of thing), NOT specific entities (such as the "
    "QID of a particular model, paper, or person). For each question "
    "call Explore_Ontology to obtain ranked schema candidates. You "
    "may issue more than one Explore_Ontology call with different "
    "schema-intent phrasings if useful. Use only IDs that the tool "
    "actually surfaced — never invent IDs. Respond with a single JSON "
    "object that matches the schema in the user message. Output ONLY "
    "the JSON, no markdown fences, no commentary. Very important: No parallel tool calls, "
    "just one tool call per response."
)

USER_PROMPT_TEMPLATE = (
    "A researcher asks:\n\n"
    '  "{topic}"\n\n'
    "Identify the MathModDB schema elements (classes, object properties, "
    "data properties, qualifier properties) that someone would need to "
    "answer this question via SPARQL. Return up to 10 IDs per category, "
    "ranked by relevance. Use bare codes without prefixes (e.g. "
    "'Q6822213', 'P558').\n\n"
    "Do NOT return specific instance QIDs. Return only schema elements — "
    "classes and properties that describe such things in general.\n\n"
    "Respond with a JSON object matching this schema:\n{schema}"
)


# ---------- run logic --------------------------------------------------


JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class RunResult:
    case: str
    query: str
    reference: CaseDefinition
    predicted: Optional[Scaffold] = None
    parsed: bool = False
    raw_response: str = ""
    explore_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None

    @property
    def precision(self) -> float:
        pred = self.predicted.all_ids() if self.predicted else set()
        if not pred:
            return 0.0
        reference_ids = self.reference.all_ids()
        return len(pred & reference_ids) / len(pred)

    @property
    def recall(self) -> float:
        reference_ids = self.reference.all_ids()
        if not reference_ids:
            return 0.0
        pred = self.predicted.all_ids() if self.predicted else set()
        return len(pred & reference_ids) / len(reference_ids)

    @property
    def f1(self) -> float:
        reference_ids = self.reference.all_ids()
        pred = self.predicted.all_ids() if self.predicted else set()
        denom = len(pred) + len(reference_ids)
        return (2 * len(pred & reference_ids) / denom) if denom else 0.0


def run_case(query: str, case_def: CaseDefinition) -> RunResult:
    schema_str = json.dumps(Scaffold.model_json_schema(), indent=2)
    user_message = USER_PROMPT_TEMPLATE.format(topic=query, schema=schema_str)

    result = RunResult(case=case_def.name, query=query, reference=case_def)
    final_text_chunks: list[str] = []

    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            mcp_servers=[
                {
                    "type": "url",
                    "url": MCP_URL,
                    "name": "mathmoddb",
                    "tool_configuration": {
                        "enabled": True,
                        "allowed_tools": ["Explore_Ontology"],
                    },
                }
            ],
            extra_headers={"anthropic-beta": "mcp-client-2025-04-04"},
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    btype = getattr(block, "type", "")
                    if btype == "mcp_tool_use":
                        name = getattr(block, "name", "?")
                        console.print(
                            f"\n[blue]→ tool:[/blue] [cyan]{name}[/cyan] ", end=""
                        )
                        if name == "Explore_Ontology":
                            result.explore_calls += 1
                    elif btype == "text":
                        console.print("\n[green]response:[/green] ", end="")
                elif event.type == "content_block_delta":
                    delta = event.delta
                    dtype = getattr(delta, "type", "")
                    if dtype == "text_delta":
                        console.print(getattr(delta, "text", ""), end="")
                    elif dtype == "input_json_delta":
                        console.print(
                            getattr(delta, "partial_json", ""), end="", style="dim"
                        )
                elif event.type == "content_block_stop":
                    console.print()

            final = stream.get_final_message()
    except Exception as e:
        result.error = repr(e)
        return result

    result.input_tokens = final.usage.input_tokens
    result.output_tokens = final.usage.output_tokens

    for block in final.content:
        if getattr(block, "type", None) == "text":
            final_text_chunks.append(getattr(block, "text", "") or "")
    result.raw_response = "\n".join(final_text_chunks).strip()

    if result.raw_response:
        cleaned = JSON_FENCE.sub("", result.raw_response).strip()
        try:
            result.predicted = Scaffold.model_validate_json(cleaned)
            result.parsed = True
        except Exception:
            ids = set(re.findall(r"\b(Q\d+|P\d+)\b", cleaned))
            if ids:
                result.predicted = Scaffold(classes=sorted(ids))
                result.parsed = True

    return result


# ---------- output -----------------------------------------------------


def render_metric_table(results: list[RunResult]) -> Table:
    t = Table(title="Explore_Ontology — scaffold retrieval", show_lines=True)
    t.add_column("case", style="cyan", no_wrap=True)
    t.add_column("P", justify="right")
    t.add_column("R", justify="right")
    t.add_column("F1", justify="right")
    t.add_column("parsed", justify="center")
    t.add_column("explore", justify="right")
    t.add_column("in tok", justify="right")
    t.add_column("out tok", justify="right")

    for r in results:
        parsed = (
            "[red]err[/red]"
            if r.error
            else ("[green]✓[/green]" if r.parsed else "[yellow]✗[/yellow]")
        )
        t.add_row(
            r.case,
            f"{r.precision:.2f}",
            f"{r.recall:.2f}",
            f"{r.f1:.2f}",
            parsed,
            str(r.explore_calls),
            str(r.input_tokens),
            str(r.output_tokens),
        )

    n = max(len(results), 1)
    n_parsed = sum(1 for r in results if r.parsed)
    t.add_section()
    t.add_row(
        "[bold]MEAN[/bold]",
        f"[bold]{sum(r.precision for r in results) / n:.2f}[/bold]",
        f"[bold]{sum(r.recall for r in results) / n:.2f}[/bold]",
        f"[bold]{sum(r.f1 for r in results) / n:.2f}[/bold]",
        f"{n_parsed}/{n}",
        f"{sum(r.explore_calls for r in results) / n:.1f}",
        f"{sum(r.input_tokens for r in results) // n}",
        f"{sum(r.output_tokens for r in results) // n}",
    )
    return t


def render_diff_table(results: list[RunResult]) -> Table:
    """Hit / missed / extra IDs per case, with labels on reference IDs."""
    t = Table(title="Per-case ID coverage (labels shown for reference IDs)", show_lines=True)
    t.add_column("case", style="cyan")
    t.add_column("hit", style="green")
    t.add_column("missed", style="red")
    t.add_column("extra (non-reference)", style="yellow")

    for r in results:
        labels = r.reference.label_lookup()
        pred_ids = r.predicted.all_ids() if r.predicted else set()
        reference_ids = r.reference.all_ids()

        hit = sorted(reference_ids & pred_ids)
        missed = sorted(reference_ids - pred_ids)
        extra = sorted(pred_ids - reference_ids)

        hit_str = "\n".join(f"{i} ({labels[i]})" for i in hit) or "—"
        missed_str = "\n".join(f"{i} ({labels[i]})" for i in missed) or "—"
        extra_str = ", ".join(extra) or "—"

        t.add_row(r.case, hit_str, missed_str, extra_str)
    return t


def render_theme_table(results: list[RunResult]) -> Table:
    grouped: dict[str, list[RunResult]] = {}
    for r in results:
        theme = r.reference.theme or "Unspecified"
        grouped.setdefault(theme, []).append(r)

    t = Table(title="Theme summary", show_lines=True)
    t.add_column("theme", style="cyan")
    t.add_column("cases", justify="right")
    t.add_column("P", justify="right")
    t.add_column("R", justify="right")
    t.add_column("F1", justify="right")

    for theme in sorted(grouped):
        items = grouped[theme]
        n = len(items)
        t.add_row(
            theme,
            str(n),
            f"{sum(r.precision for r in items) / n:.2f}",
            f"{sum(r.recall for r in items) / n:.2f}",
            f"{sum(r.f1 for r in items) / n:.2f}",
        )
    return t


def main() -> None:
    if not CASES_PATH.exists():
        console.print(f"[red]case file not found:[/red] {CASES_PATH}")
        return

    cases = load_cases(CASES_PATH)
    console.print(f"[dim]loaded {len(cases)} cases from {CASES_PATH}[/dim]")

    results: list[RunResult] = []
    for query, case_def in cases.items():
        console.print(Rule(f"[bold]{case_def.name}[/bold]"))
        r = run_case(query, case_def)
        results.append(r)
        if r.error:
            console.print(f"[red]error:[/red] {r.error}")
        else:
            console.print(
                f"\n[dim]R={r.recall:.2f} "
                f"explore={r.explore_calls} "
                f"in={r.input_tokens} out={r.output_tokens}[/dim]"
            )

    console.print()
    console.print(render_metric_table(results))
    console.print()
    console.print(render_theme_table(results))
    console.print()
    console.print(render_diff_table(results))


if __name__ == "__main__":
    main()
