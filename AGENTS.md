# Engineering Rules (for AI Assistants)

Authoritative coding instructions for this repository. Linked from:
- `.cursor/rules/` (Cursor)
- `.github/copilot-instructions.md` (Copilot)
- `CLAUDE.md` (Claude Code)
- `AGENTS.md` (OpenAI Codex)

---

## Project Structure & Naming

```
src/vardoger/          # shared core — history reading, analysis, prompt generation
plugins/cursor/        # Cursor MCP server config, install script
plugins/claude-code/   # Claude Code plugin manifest, skills
plugins/codex/         # Codex plugin manifest, skills
```

| Kind | Path pattern |
|---|---|
| History adapters | `src/vardoger/history/<platform>.py` |
| Prompt writers | `src/vardoger/writers/<platform>.py` |
| AI prompts | `src/vardoger/prompts/*.md` (or `plugins/<platform>/prompts/` if platform-specific) |
| Plugin manifests | `plugins/<platform>/.<tool>-plugin/plugin.json` |
| Skills | `plugins/<platform>/skills/<name>/SKILL.md` |
| Tests | co-located `test_*.py` next to the code they test |

---

## Before You Code

- **Find the module boundary**: locate the nearest `pyproject.toml` and treat it as the unit of build, test, and dependency rules.
- **Preserve layering**: shared core lives in `src/vardoger/`, platform-specific code in `plugins/<platform>/`. Don't mix them.
- **Prefer configuration over ad-hoc constants**: use a config class and env vars rather than scattering `os.getenv` calls.
- **Avoid duplication**: if you see near-identical blocks, centralize them.

---

## Code Review Priorities

These are the patterns reviewers consistently flag:

- **Module boundaries & dependency direction**
  - Shared types belong in `src/vardoger/`, not inside a plugin.
  - Plugin modules should not import from other plugins; dependencies flow inward to the shared core.

- **Config & safety**
  - Put env/config interpretation in a config class, not sprinkled across code.
  - Add explicit enablement flags for destructive or side-effectful operations.

- **Code clarity**
  - Keep method/variable names aligned with actual behavior.
  - Keep private helper functions at the bottom of the file.
  - PR titles/descriptions must match the actual scope.

- **Testing**
  - Prefer simple, readable tests over elaborate fixtures.
  - Add unit tests for new non-trivial logic.
  - Assert whole expected objects in a single comparison, not field-by-field.

- **Serialization & data**
  - Don't build JSON by string concatenation; construct objects and serialize.
  - Keep templates centralized and reusable.

- **Performance**
  - Don't recreate immutable instances on every call; reuse a single instance when safe.
  - Prefer `orjson` for heavy JSON workloads.

---

## Git Workflow

### Commits
- **Subject**: imperative summary, one line. Never mention AI assistants (no `Co-Authored-By`).
- **Dependency bumps**: `bump <package> to <version>` (commit both `pyproject.toml` and `uv.lock`).

### Pull Requests
- **Title**: short imperative summary.
- **Description**: say what and why. Don't list changed files. Don't mention AI assistants.
- **Merge**: rebase and merge to `main`, delete branch after merge.

---

## Python

### Runtime & Dependencies
- **Python version**: ≥3.11 (follow `pyproject.toml`).
- **Package manager**: [uv](https://docs.astral.sh/uv/)
  - Install: `uv sync`
  - Add runtime dep: `uv add <pkg>`
  - Add dev dep: `uv add --group dev <pkg>`
  - Lock update: `uv lock`

### Quality Checks

Run these before pushing — all must pass:

```bash
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
uv run mypy src/                     # type check
uv run pytest                        # tests
uv run pytest --cov=vardoger         # coverage
```

Quick-fix formatting and auto-fixable lint issues:

```bash
uv run ruff format .                 # auto-format
uv run ruff check --fix .            # auto-fix lints
```

### Code Standards
- **Data structures**:
  - Use `pydantic.BaseModel(frozen=True)` for DTOs/data containers.
  - `attrs.define` is acceptable for service/container classes.
  - Avoid stdlib `dataclasses` in application code.
- **Typing**:
  - Add `from __future__ import annotations` in every module.
  - MyPy strict mode: `disallow_untyped_defs`, `check_untyped_defs`.
  - Prefer precise types and immutable collections (`frozenset`, `tuple`).
- **Formatting**: enforced by ruff (replaces black + isort + autoflake). See `[tool.ruff]` in `pyproject.toml`.

### Testing
- Framework: pytest with co-located test files (`test_*.py` next to the code they test).
- Target coverage: ≥90% for core modules.
- All tests must pass before commit/push.

### Architecture Patterns
- **Configuration**: centralize env access (e.g., `Config.from_env()`), avoid scattered `os.getenv`.
- **Error handling**: raise clear exceptions with actionable messages.
- **Logging**: `getLogger(__name__)`, structured and context-rich, never log PII or secrets.
- **Imports**: absolute imports within the `vardoger` package namespace.
- **Immutability**: immutable DTOs, avoid mutating inputs.
- **Prompts**: store as standalone `.md` files under `src/vardoger/prompts/`, never as inline strings. Python code loads them at runtime.
