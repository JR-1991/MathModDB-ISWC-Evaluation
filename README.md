# MathModDB MCP Server: Schema Scaffold Retrieval Evaluation

## 1. Scope

This artifact evaluates whether a model, constrained to the [MathModDB MCP](https://github.com/MaRDI4NFDI/MathModDB-MCP) tool `Explore_Ontology`, can retrieve relevant **schema elements** (classes and properties) for natural-language research questions.

The evaluation script is `main.py`. Benchmark cases are provided in `cases.json`.

## 2. Repository Contents

- **`main.py`** (400 lines): End-to-end evaluation runner. Loads cases, invokes Claude with MCP tools, parses responses, scores predictions against reference sets, and produces metric summary tables.
- **`cases.json`**: Benchmark cases with natural-language queries, case metadata (name, theme), and reference schema IDs grouped by type (classes, object/data/qualifier properties).
- **`pyproject.toml`**: Python `>=3.13` requirement and dependency declarations (`anthropic`, `pydantic`, `rich`, `dotenv`).
- **`.env`** (user-created): Stores `ANTHROPIC_API_KEY` and optional configuration variables.
- **`README.md`** (this file): Documentation, setup instructions, and evaluation methodology.

## 3. Task Definition

For each natural-language query in `cases.json`, the script:

1. Requests schema IDs (`Q...` and `P...`)
2. Restricts tool use to `Explore_Ontology`
3. Parses the model response into structured predictions
4. Compares predicted IDs against the reference set

## 4. Evaluation Metric

The reported primary metric is **recall** over ID sets:

`recall = |predicted ∩ reference| / |reference|`

The script additionally reports **precision** and **F1** for each case and in the aggregate summary:

- `precision = |predicted ∩ reference| / |predicted|`
- `recall = |predicted ∩ reference| / |reference|`
- `F1 = 2 * precision * recall / (precision + recall)`

The script reports:

- Per-case precision, recall, and F1
- Mean precision, recall, and F1 over all cases
- Per-case hit/missed/extra ID analysis
- Parse status, tool-call count, and token usage

## 5. Environment and Requirements

- Python `>=3.13` (required for sys.monitoring and newer Anthropic SDK features)
- Valid Anthropic API key (`ANTHROPIC_API_KEY`)
- Network access to the configured MathModDB MCP endpoint (default: https://9f0bd004-46b8-403b-9f67-30d65c0a01de.ma.bw-cloud-instance.org/mathmoddb/mcp)
- ⚠️ **API Costs**: Each evaluation run incurs charges against your Anthropic account. Cost scales with number of cases and model complexity.

Dependencies (from `pyproject.toml`):

- `anthropic>=0.97.0`
- `dotenv>=0.9.9`
- `pydantic>=2.13.3`
- `rich>=15.0.0`

## 6. Installation

### Option A (recommended): `uv`

```bash
uv sync
```

### Option B: `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install anthropic dotenv pydantic rich
```

## 7. Configuration

Create `.env` in the repository root:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Optional environment variables:

- `MATHMODDB_MCP_URL` (default: `https://9f0bd004-46b8-403b-9f67-30d65c0a01de.ma.bw-cloud-instance.org/mathmoddb/mcp` — hardcoded fallback in `main.py`)
- `CLAUDE_MODEL` (default: `claude-sonnet-4-6` — adjust for cost/performance tradeoffs)
- `CASES_PATH` (default: `cases.json` — path to benchmark case definitions)

## 8. Reproducing Results

Run:

```bash
python main.py
```

### Output Tables

The script prints three tables:

#### 1. **Metric Table** (Per-case evaluation)

| Column | Meaning |
| --- | --- |
| `case` | Case name slug |
| `P` | Precision: $\frac{\text{predicted} \cap \text{reference}}{\text{predicted}}$ (0–1) |
| `R` | Recall: $\frac{\text{predicted} \cap \text{reference}}{\text{reference}}$ (0–1) |
| `F1` | Harmonic mean: $\frac{2 \cdot P \cdot R}{P + R}$ |
| `parsed` | Parse status: `✓` (success), `✗` (fallback regex), `err` (error) |
| `explore` | Number of `Explore_Ontology` tool calls for this case |
| `in tok` | Input tokens consumed |
| `out tok` | Output tokens generated |
| **MEAN** | Row showing aggregated metrics across all cases |

#### 2. **Theme Summary** (Grouped by topic area)

| Column | Meaning |
| --- | --- |
| `theme` | Topic cluster (e.g., "Formulations & equations", "Model transformations") |
| `cases` | Number of cases in this theme |
| `P`, `R`, `F1` | Mean metrics for cases in this theme |

#### 3. **Per-case Coverage** (ID-level diagnostics)

For each case:
- **hit**: IDs successfully predicted (with reference labels)
- **missed**: IDs in reference but not predicted (with reference labels)
- **extra**: IDs predicted but not in reference (false positives)

## 9. Case Data Format

The benchmarks are defined in the `cases.json` and consist of typical queries from mathematics.

`cases.json` is expected to follow:

```json
{
  "Natural language query": {
    "name": "short_case_name",
    "theme": "mapping_query_to_theme",
    "classes": [{ "id": "Q...", "label": "..." }],
    "object_properties": [{ "id": "P...", "label": "..." }],
    "data_properties": [{ "id": "P...", "label": "..." }],
    "qualifiers": [{ "id": "P...", "label": "..." }]
  }
}
```

### Topic-to-Case Mapping

The benchmark cases are grouped into four high-level theme areas to support thematic analysis of retrieval quality.

| Theme | Cases |
| --- | --- |
| Formulations & equations | `coupling_conditions_pde`, `defining_formulas`, `stochastic_modelling` |
| Model transformations | `finite_element_discretization`, `linearization`, `dimensional_analysis` |
| Tasks & problem types | `computational_tasks`, `initial_boundary_problems` |
| Domain & provenance | `creator_attribution`, `research_field_domain`, `enzyme_kinetics` |

The theme information is stored as a `theme` field in each case entry in `cases.json`, and the evaluator also prints an aggregate summary table grouped by theme in `main.py`.

## 11. Error Handling & Validation

### Parse Status Column

- `[green]✓[/green]`: Response parsed successfully as valid JSON
- `[yellow]✗[/yellow]`: JSON parsing failed; fallback regex extraction of `Q...` and `P...` IDs was used (case still scorable)
- `[red]err[/red]`: Critical error (API call failed, malformed case definition, etc.); case not scored

### Common Errors

| Error | Likely Cause | Fix |
| --- | --- | --- |
| `Invalid API key` | `ANTHROPIC_API_KEY` is missing or wrong | Check `.env` file |
| `Connection refused` | MCP endpoint unreachable | Verify `MATHMODDB_MCP_URL` and network connectivity |
| `Case file not found` | `cases.json` missing or `CASES_PATH` wrong | Ensure `cases.json` exists in the repository root |
| `JSON decode error` | Model response violates schema | Check system prompt compliance in `main.py` |

## 12. Debugging & Development

### Run a single case

To debug a specific case, edit `main.py` to run only that case or check the per-case output from `python main.py`:

```
─────────────────────────────────────────────────────────
 CASE_NAME
─────────────────────────────────────────────────────────

→ tool: Explore_Ontology [input JSON...]
response: {...JSON response...}

[dim]R=0.85 explore=2 in=1234 out=567[/dim]
```

### Adjust model or costs

To use a cheaper/faster model (e.g., Haiku), set:

```bash
export CLAUDE_MODEL=claude-haiku-3-5
python main.py
```

See [Anthropic Models](https://docs.anthropic.com/en/docs/about/models/overview) for available options.

## 13. Reproducibility Notes

- Results may vary across runs due to model nondeterminism and upstream service
  behavior.
- The script constrains tool usage to `Explore_Ontology` to reduce variance in
  retrieval pathways.
- If strict JSON parsing fails, a regex fallback extracts `Q...` and `P...` IDs
  so cases remain scorable.
- System prompt enforces "No parallel tool calls, just one tool call per response" to ensure consistent retrieval patterns.


