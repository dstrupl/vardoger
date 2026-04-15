# Coding Conventions

## Project Layout

### 1. Shared core in `src/`, tool-specific code in `plugins/`

All platform-agnostic logic lives under `src/vardoger/`. This includes the data model,
history adapters, analysis pipeline, and shared utilities.

Platform-specific integration code (plugin manifests, skills, install scripts, and
platform-specific tests) lives under `plugins/<platform>/`.

```
src/vardoger/          # shared core — history reading, analysis, prompt generation
plugins/cursor/        # Cursor MCP server config, install script
plugins/claude-code/   # Claude Code plugin manifest, skills
plugins/codex/         # Codex plugin manifest, skills
```

### 2. AI prompts live in `.md` files

All prompts sent to AI models must be stored as standalone Markdown files, not
inline strings in Python code. Python code loads them at runtime.

This keeps prompts easy to read, edit, review, and evaluate independently of the
code that invokes them.

```
src/vardoger/prompts/          # shared analysis prompts (Phase 2+)
plugins/<platform>/prompts/    # platform-specific prompts if needed
```

### 3. Tests are co-located

Tests live next to the code they test, not in a separate top-level directory.

- Tests for shared code go in `src/vardoger/` (e.g., `src/vardoger/history/test_cursor.py`)
- Tests for plugin-specific code go in `plugins/<platform>/` (e.g., `plugins/cursor/test_writer.py`)

Test files are named `test_*.py` and discovered by pytest automatically.

**All tests must pass before commit/push.**

## Naming

- History adapters: `src/vardoger/history/<platform>.py`
- Prompt writers: `src/vardoger/writers/<platform>.py`
- Plugin manifests: `plugins/<platform>/.<tool>-plugin/plugin.json`
- Skills: `plugins/<platform>/skills/<name>/SKILL.md`
