# Shared plugin sources

The analyze skill body is a single template shipped as a package resource at
[`src/vardoger/prompts/analyze_skill_body.md`](../../src/vardoger/prompts/analyze_skill_body.md).
It is consumed by two paths:

- Build time — [`scripts/render-skills.py`](../../scripts/render-skills.py) writes
  the rendered `SKILL.md` into each `plugins/<platform>/skills/analyze/` so the
  marketplace-shipped plugins stay in lock-step.
- Runtime — `vardoger setup {claude-code|codex|openclaw}` calls
  `vardoger.prompts.analyze_skill_body()` and writes the same rendered file
  into `~/.vardoger/plugins/<platform>/skills/analyze/SKILL.md`.

## Regenerate

From the repo root:

```bash
uv run scripts/render-skills.py
```

CI runs the same command with `--check` to fail if the rendered outputs drift
from the template (see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).
