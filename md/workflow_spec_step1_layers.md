# Spec Generation — Step 1: Write `generate_topdown_layers.py`

This document is fully self-contained. Read it and implement the script exactly as specified.

---

## What This Script Does

Build a per-phase call graph and compute topological layers. Output: `fm_agent/spec_prompts/phase_NN_topdown_layers.json` for each phase.

---

## Prerequisites

The following should already exist:

```
<repo-root>/
├── fm_agent/
│   ├── phases.json                         # machine-readable phase definitions
│   ├── spec_prompts/
│   │   ├── system_prompt.md               # behavioral spec rules
│   │   └── domain_context/
│   │       ├── engine_overview.txt          # system architecture and encoding conventions
│   │       └── phase_NN_types.txt           # types and invariants per phase
│   └── extracted_functions/                # one function per file
│       └── <xxx>/
│           └── <yyy>/
│               └── <zzz-ext>/              # source filename with dot replaced by hyphen
│                   └── <function_name>.<ext>
```

### `fm_agent/phases.json` Schema Reference

```json
{
  "project": "<project_name>",
  "languages": ["<lang1, e.g. cpp>", "<lang2, e.g. python>"],
  "file_extensions": ["<ext1, e.g. cpp>", "<ext2, e.g. py>"],
  "phases": [
    {
      "phase": 1,
      "name": "<Human-readable phase name>",
      "description": "<One sentence: what this phase does in the data pipeline>",
      "modules": [
        {
          "name": "<module_name>",
          "source_files": ["<path/to/source>", "..."]
        }
      ],
      "depends_on_phases": []
    }
  ]
}
```

**Field rules:**

- `project` — basename of `proj_dir` (the directory passed to `main.py`)
- `languages` — list of canonical lowercase language identifiers used in the project
- `file_extensions` — list of file extensions without leading dot, one per language
- `phases[*].phase` — 1-indexed integer, unique, ascending
- `phases[*].modules[*].name` — matches the subdirectory name of the module
- `phases[*].modules[*].source_files` — paths relative to `proj_dir` (not the repository root)
- `phases[*].depends_on_phases` — list of phase numbers whose outputs this phase consumes

---

## Algorithm

### 1.1 Configuration

Load phase configuration from `fm_agent/phases.json` at the repo root. **Do not hardcode `PHASE_META` or `PHASE_FILES`.**

```python
import json
from pathlib import Path

phases_json = json.loads(Path("fm_agent/phases.json").read_text())
PROJECT     = phases_json["project"]
EXTS        = phases_json["file_extensions"]

PHASE_META  = {p["phase"]: p["name"]    for p in phases_json["phases"]}
PHASE_FILES = {p["phase"]: [m["name"] for m in p["modules"]]
               for p in phases_json["phases"]}
```

`PHASE_FILES` maps phase number → list of `module_name`. To locate extracted functions for a module, look up its `source_files` in `fm_agent/phases.json` and derive each extracted directory: for source file `xxx/yyy/zzz.ext`, the extracted functions are in `fm_agent/extracted_functions/xxx/yyy/zzz-ext/`.

### 1.2 Collect Files Per Phase

For each phase, find all modules in that phase via `fm_agent/phases.json`. For each module, iterate its `source_files` entries. For each source file `xxx/yyy/zzz.ext`, derive the extension from the filename and glob all matching files from `fm_agent/extracted_functions/xxx/yyy/zzz-ext/`.

### 1.3 Assign Fully-Qualified Names (FQNs)

Each file gets an FQN derived from its path (strip the `fm_agent/extracted_functions/` prefix and the function file's extension, then join path components with `::` as a universal separator regardless of the source language):
- `fm_agent/extracted_functions/src/engine/loader-cpp/loadData.cpp` → FQN `src::engine::loader-cpp::loadData`
- `fm_agent/extracted_functions/lib/queries/q1-py/run_q1.py` → FQN `lib::queries::q1-py::run_q1`
- `fm_agent/extracted_functions/pkg/loader-go/load_data.go` → FQN `pkg::loader-go::load_data`

The "stem" of an FQN is its last `::` component (e.g., `loadData`, `run_q1`, `load_data`).

### 1.4 Build Call Graph by Static Analysis

For each file:
1. Read its source text and strip comments (replace their contents with whitespace to preserve positions) so that identifiers inside comments are not treated as call sites
2. Find call sites using a language-aware regex:
   - **C++/Java/TypeScript/JavaScript:** `\b(\w+)\s*(?:<[^>]*>)?\s*\(` (identifier, optional template args, open paren). Note: nested template args like `foo<vector<int>>()` will mis-parse — acceptable because step 3 filters to known stems
   - **Rust:** `\b(\w+)\s*(?:::<[^>]*>)?\s*\(` (identifier, optional turbofish `::< >`, open paren)
   - **Go:** `\b(\w+)\s*(?:\[[^\]]*\])?\s*\(` (identifier, optional type params `[T]`, open paren)
   - **Python/Ruby/Shell/SQL and other languages without generics:** `\b(\w+)\s*\(` (identifier, open paren)
3. Keep only identifiers that match the **stem** of another known function **in the same phase**
4. Exclude language keywords (e.g., `if`, `else`, `for`, `return`, `class`, etc., plus any additional built-in identifiers that are not user-defined functions)
5. Result: `callees_map[fqn]` = set of FQNs called by this function
6. Derive: `callers_map[fqn]` = set of FQNs that call this function

### 1.5 Topological Layer Computation

**Standard case (Kahn's algorithm):**
- Layer 0: functions with no same-phase callers (`callers_map[fqn] ∩ phase_fqns == ∅`)
- Layer N: functions whose all same-phase callers are already assigned to layers 0..N-1
- Repeat until all functions are assigned

**Cycle handling (mutual recursion):**
When no progress can be made (remaining functions all have unassigned callers), detect strongly connected components (SCCs) using Tarjan's or Kosaraju's algorithm:
1. Build a subgraph of remaining functions with edges only within remaining functions
2. Compute SCCs
3. Assign SCCs to sub-layers topologically (an SCC can be assigned to a sub-layer once all SCCs that call it are already assigned)
4. Each SCC of size > 1 is a true cycle — mark its layer with `"cycle_resolution": true`
5. Assign all functions in an SCC to the same layer

### 1.6 Output JSON Schema

```json
{
  "phase": 3,
  "phase_name": "In-Memory Database Construction",
  "total_functions": 21,
  "total_layers": 3,
  "layers": [
    {
      "layer": 0,
      "functions": [
        {
          "name": "src::engine::builder-cpp::build",
          "file": "fm_agent/extracted_functions/src/engine/builder-cpp/build.<ext>",
          "unit": "builder",
          "phaseN_callers": [],
          "phaseN_callees": ["src::engine::builder-cpp::get_column", "src::engine::builder-cpp::build_date_offsets"],
          "all_callees": ["src::engine::builder-cpp::get_column", "src::engine::builder-cpp::build_date_offsets"]
        }
      ]
    },
    {
      "layer": 1,
      "cycle_resolution": true,
      "functions": [ ... ]
    }
  ]
}
```

Use the actual phase number in key names: `phase3_callers`, `phase3_callees`. `all_callees` includes callees in any phase (for reference). `cycle_resolution` key is only present (and set to `true`) on cycle layers.

### 1.7 CLI Interface

```
python3 fm_agent/spec_prompts/generate_topdown_layers.py          # all phases
python3 fm_agent/spec_prompts/generate_topdown_layers.py 1 3 5   # specific phases
```

---

## Verification

After writing the script, run it:

```bash
python3 fm_agent/spec_prompts/generate_topdown_layers.py
```

Verify that `fm_agent/spec_prompts/phase_NN_topdown_layers.json` files have been generated for each phase in `fm_agent/phases.json`.
