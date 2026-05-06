# ISWC Artifact README: Schema Scaffold Retrieval Evaluation

## 1. Scope

This artifact evaluates whether an LLM, constrained to the MathModDB MCP tool `Explore_Ontology`, can retrieve relevant **schema elements** (classes and properties) for natural-language research questions.

The evaluation script is `main.py`. Expected annotations are provided in `cases.json`.

## 2. Repository Contents

- `main.py`: end-to-end evaluation runner
- `cases.json`: benchmark cases with expected schema IDs and labels
- `pyproject.toml`: Python and dependency specification

## 3. Task Definition

For each natural-language query in `cases.json`, the script:

1. Prompts the model to return schema IDs (`Q...` and `P...`)
2. Restricts tool use to `Explore_Ontology`
3. Parses the model response into structured predictions
4. Compares predicted IDs against the expected set

## 4. Evaluation Metric

The reported primary metric is **recall** over ID sets:

`recall = |predicted ∩ expected| / |expected|`

The script reports:

- Per-case recall
- Mean recall over all cases
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
- `GOLD_PATH` (default: `cases.json`)

## 8. Reproducing Results

Run:

```bash
python main.py
```

The script executes all cases in `GOLD_PATH` and prints:

- A per-case live execution trace
- An aggregate metric table
- A per-case coverage table (hit, missed, extra IDs)

## 9. Expected Data Format

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

## 10. Reproducibility Notes

- Results may vary across runs due to model nondeterminism and upstream service
  behavior.
- The script constrains tool usage to `Explore_Ontology` to reduce variance in
  retrieval pathways.
- If strict JSON parsing fails, a regex fallback extracts `Q...` and `P...` IDs
  so cases remain scorable.
