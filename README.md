# MathModDB MCP Server: Schema Scaffold Retrieval Evaluation

## 1. Scope

This artifact evaluates whether a model, constrained to the MathModDB MCP tool `Explore_Ontology`, can retrieve relevant **schema elements** (classes and properties) for natural-language research questions.

The evaluation script is `main.py`. Benchmark cases are provided in `cases.json`.

## 2. Repository Contents

- `main.py`: end-to-end evaluation runner
- `cases.json`: benchmark cases with expected schema IDs and labels
- `pyproject.toml`: Python and dependency specification

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

- Python `>=3.13`
- Anthropic API key
- Network access to the configured MathModDB MCP endpoint

Dependencies (from `pyproject.toml`):

- `anthropic`
- `dotenv`
- `pydantic`
- `rich`

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

- `MATHMODDB_MCP_URL` (default: endpoint embedded in `main.py`)
- `CLAUDE_MODEL` (default: `claude-sonnet-4-6`)
- `CASES_PATH` (default: `cases.json`)

## 8. Reproducing Results

Run:

```bash
python main.py
```

The script executes all cases in the configured case file path (`CASES_PATH`, default `cases.json`) and prints:

- A per-case live execution trace
- A summary table with columns `P`, `R`, and `F1` for each case
- An aggregate row showing mean precision, recall, and F1 across all cases
- A per-case coverage table (hit, missed, extra IDs)

## 9. Case Data Format

The benchmarks are defined in the `cases.json` and consist of typical queries from mathematics.

`cases.json` is expected to follow:

```json
{
  "Natural language query": {
    "name": "short_case_name",
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

## 10. Reproducibility Notes

- Results may vary across runs due to model nondeterminism and upstream service
  behavior.
- The script constrains tool usage to `Explore_Ontology` to reduce variance in
  retrieval pathways.
- If strict JSON parsing fails, a regex fallback extracts `Q...` and `P...` IDs
  so cases remain scorable.

## 11. Topic-to-Case Mapping

The benchmark cases are grouped into four high-level theme areas to support thematic analysis of retrieval quality.

| Theme | Cases |
| --- | --- |
| Formulations & equations | `coupling_conditions_pde`, `defining_formulas`, `stochastic_modelling` |
| Model transformations | `finite_element_discretization`, `linearization`, `dimensional_analysis` |
| Tasks & problem types | `computational_tasks`, `initial_boundary_problems` |
| Domain & provenance | `creator_attribution`, `research_field_domain`, `enzyme_kinetics` |

The theme information is stored as a `theme` field in each case entry in `cases.json`, and the evaluator also prints an aggregate summary table grouped by theme in `main.py`.
