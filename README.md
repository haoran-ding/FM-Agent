# FM-Agent: Scaling Formal Methods to Large Systems via LLM-Based Hoare-Style Reasoning

FM-Agent is the first framework that realizes automated compositional reasoning for large-scale systems (e.g., [Claude's C Compiler](https://github.com/anthropics/claudes-c-compiler) with 143K LoC).
It is presented in the paper "[FM-Agent: Scaling Formal Methods to Large Systems via LLM-Based Hoare-Style Reasoning](https://arxiv.org/abs/2604.11556)".

The [website](http://fm-agent.ai/) of FM-Agent provides an online service for reasoning about codebases. You can try it easily!

> **⚠️ Warning**: The effectiveness of this framework is heavily influenced by the capability of the underlying model. Weaker models may produce hallucinations, leading to incorrect reasoning conclusions. We recommend using models with strong reasoning abilities (Claude Opus 4.6/4.7, Claude Sonnet 4.6) for more reliable results.

## Table of Contents

- [File Structure](#file-structure)
- [Environment Setup](#environment-setup)
  - [Requirements](#requirements)
  - [Install Dependencies](#install-dependencies)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Important Notes](#important-notes)
- [Citation](#citation)
- [Contact](#contact)


## File Structure

```
|-- main.py                # Entry point and pipeline orchestrator
|-- config.py              # Configuration constants (model, granularity, concurrency)
|-- install.sh             # Dependency installation script
|-- src/                   # Core source modules (extraction, reasoning, LLM interaction, etc.)
|-- md/                    # Workflow of FM-Agent to guide LLMs
```

## Environment Setup

### Requirements

- Ubuntu (24.04 LTS is tested)
- Python 3.12
- pip >= 23
- [openai](https://pypi.org/project/openai/) 2.15.0
- [OpenCode](https://github.com/opencode-ai/opencode) 1.4.6
- [Bun](https://bun.sh/)
- [oh-my-opencode](https://www.npmjs.com/package/oh-my-opencode) plugin (installed via `bunx`)
- [OpenRouter](https://openrouter.ai/) API key

### Install Dependencies

Set your [OpenRouter](https://openrouter.ai/) API key as an environment variable. Note that FM-Agent only supports the OpenRouter API key for now, because it will concurrently invoke LLMs. OpenRouter is flexible in RPM (requests per minute) and TPM (tokens per minute).


```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Then, all of the above dependencies (except Ubuntu and Python) can be installed via the provided script:

```bash
./install.sh
```

(Optional) If needed, you can manually set the default LLM model and API key of OpenCode in its configuration file.

**Important:** FM-Agent automatically derives test cases based on the reasoning process to trigger potential bugs, which help developers locate and fix them. Before running FM-Agent, please ensure the execution environment for test cases is ready, and if necessary, specify how to run test cases in `md/bug_validator.md`. If you do not specify, the agent will autonomously decide the execution method.

## Configuration

Key parameters can be adjusted in [config.py](config.py).

| Parameter | Default | Description |
|---|---|---|
| `LLM_MODEL` | `anthropic/claude-sonnet-4.6` | Default model used as the fallback for all task-specific model settings |
| `OPENCODE_SETUP_MODEL` | `LLM_MODEL` | Model used by OpenCode for codebase understanding, phase planning, and domain context generation |
| `OPENCODE_SPEC_MODEL` | `LLM_MODEL` | Model used by OpenCode for batch behavioral spec generation |
| `OPENCODE_BUG_VALIDATION_MODEL` | `LLM_MODEL` | Model used by OpenCode to validate `MISMATCH` results with probe scripts and bug reports |
| `REASONER_POST_CONDITION_MODEL` | `LLM_MODEL` | Model used by direct llm calls to generate block post-conditions |
| `REASONER_SPEC_CHECK_MODEL` | `LLM_MODEL` | Model used by direct llm calls to check whether actual post-conditions violate specs |
| `LLM_OPENROUTER_API_KEY` | (env) | OpenRouter API key (read via `os.environ.get("OPENROUTER_API_KEY")`) |
| `LLM_OPENROUTER_API_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |

**Important Note:** We strongly recommend using Claude Opus 4.6/4.7 or Claude Sonnet 4.6, as other models may lack the reasoning capabilities required by FM-Agent and may not be able to effectively uncover bugs. In addition, please use an API key with access to Claude models, since FM-Agent invokes OpenCode, which may potentially access Claude models.

(Optional) FM-Agent uses oh-my-opencode plugin to enhance OpenCode. The comment-checker hook built into this plugin should be disabled, otherwise it may intercept every comment block that FM-Agent writes, which are specifications of functions. It may force the agent to waste tokens justifying or removing them.
You can open your oh-my-opencode config file (typically ~/.config/opencode/oh-my-opencode.json) and add disabled_hooks:

```json
{
  "disabled_hooks": ["comment-checker"],
}
```


## Quick Start

```bash
python3 main.py <proj_dir>
```

| Argument | Description |
|---|---|
| `proj_dir` | Directory of codebase that you want to check correctness |

### Output

FM-Agent creates an `fm_agent/` directory under your codebase directory. The key outputs are:

#### Bug Reports (`fm_agent/bug_validation/<bug_id>.md`)

Each confirmed or investigated bug produces a Markdown report containing:

| Section | Content |
|---|---|
| Specification Claim | The post-condition that the function specification requires |
| Actual Behavior | The post-condition that the code actually implements |
| Code Evidence | The specific code statements (with line numbers) that cause the violation |
| Trigger Condition | A description of the condition that triggers the bug |
| How to Trigger | Concrete input parameters, expected vs. actual output, and reproduction steps |
| Probe Script | The full test script used to confirm the bug |
| Probe Output | Raw stdout from executing the probe script |

A companion `<bug_id>.result.json` is generated alongside each report, containing machine-readable fields such as `confirmation_status` (`confirmed`, `not_confirmed`, or `error`), `probe_script` path, and `trigger_summary`.

A `summary.json` file in `fm_agent/bug_validation/` aggregates all bug results with counts of total reported, confirmed, not confirmed, and errored bugs.

#### Log File (`fm_agent/fm_agent.log`)

A single log file records the entire pipeline execution, including file extraction progress, reasoning submissions and completions, network errors and retries, and the final reasoning summary statistics. The log level is `INFO` and the format is `%(asctime)s [%(levelname)s] %(message)s`.

## Important Notes

1. FM-Agent will create an `fm_agent/` directory under your codebase directory. Make sure there is no name conflict.
2. The markdown files under `md/` provide general instructions that guide the agent's reasoning process. Customizing them for your specific project can improve accuracy and help uncover more bugs. For example, you can include project documentation to give the agent deeper understanding of your codebase, or if you are reasoning about a compiler, modify `md/bug_validator.md` to instruct the agent to compare outputs against a reference implementation (e.g., GCC).
3. **Supported languages**: Rust, C, C++, Python, Java, Go, CUDA, JavaScript, TypeScript, ArkTS.

## Citation

If you use FM-Agent in your projects or research, please kindly cite our [paper](https://arxiv.org/abs/2604.11556):

```bibtex
@misc{ding2026fmagent,
Author = {Haoran Ding and Zhaoguo Wang and Haibo Chen},
Title = {FM-Agent: Scaling Formal Methods to Large Systems via LLM-Based Hoare-Style Reasoning},
Year = {2026},
Eprint = {arXiv:2604.11556},
}
```

## Contact

If you have any questions, please submit an issue or send [email](mailto:nhaorand@gmail.com).
