# Contributing to vardoger

Thanks for taking the time to contribute! This document walks through the full
workflow for submitting a pull request. For a one-paragraph version, see the
[Contributing section in the README](README.md#contributing).

Coding standards, project layout, and per-module expectations live in
[AGENTS.md](AGENTS.md) — please skim it before your first change.

## Prerequisites

- Python 3.11 or newer (CI tests 3.11, 3.12, 3.13).
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency
  management.
- A GitHub account for forking the repository.

## 1. Fork and clone

1. Click **Fork** on [github.com/dstrupl/vardoger](https://github.com/dstrupl/vardoger)
   to create your own copy.
2. Clone your fork and add the upstream remote so you can keep it in sync:

   ```bash
   git clone https://github.com/<your-username>/vardoger.git
   cd vardoger
   git remote add upstream https://github.com/dstrupl/vardoger.git
   ```

3. Install dependencies:

   ```bash
   uv sync
   ```

## 2. Create a topic branch

Base your work on an up-to-date `main`:

```bash
git fetch upstream
git checkout -b my-change upstream/main
```

Use a short, descriptive branch name (e.g. `fix-cursor-timestamp-parsing`,
`add-openclaw-staleness-check`).

## 3. Make your change

- Follow the conventions in [AGENTS.md](AGENTS.md): Pydantic for JSON I/O,
  `from __future__ import annotations` in every module, absolute imports within
  the `vardoger` package, prompts as `.md` files (not inline strings).
- Add or update tests under `tests/` to cover new behavior. Coverage must stay
  at or above 80% overall.
- Keep commits focused and use imperative-mood subjects (e.g. `fix cursor
  transcript edge case`, not `Fixed a bug`). Do **not** add AI co-author
  trailers.

## 4. Run the quality gates locally

CI will run the same checks on your PR; running them locally first avoids the
back-and-forth. The one-liner:

```bash
uv run ruff check . \
  && uv run ruff format --check . \
  && uv run mypy src/ \
  && uv run pytest --cov=vardoger --cov-fail-under=80
```

Individual commands, if you want to iterate on one at a time:

| Check | Command |
| --- | --- |
| Lint | `uv run ruff check .` |
| Auto-fix lint | `uv run ruff check --fix .` |
| Format | `uv run ruff format .` |
| Format check | `uv run ruff format --check .` |
| Type check | `uv run mypy src/` |
| Tests + coverage | `uv run pytest --cov=vardoger --cov-fail-under=80` |

The security job in CI additionally runs:

```bash
uv run --with bandit bandit -r src/ -q
uv run --with pip-audit pip-audit --skip-editable
```

You can run these locally too, but they rarely fail on feature PRs.

## 5. Push and open a PR

```bash
git push -u origin my-change
```

Then open a pull request against `dstrupl/vardoger:main`. In the PR
description:

- Say **what** the change does and **why** (not the list of touched files).
- Link any related issue.
- Mention anything reviewers should pay extra attention to (risk, migrations,
  follow-ups).

## 6. What happens on your PR

- GitHub runs the `CI` workflow automatically:
  - `test` job: lint, format check, mypy, and pytest with an 80% coverage
    floor on Python 3.11, 3.12, and 3.13.
  - `security` job: `bandit` plus `pip-audit`.
- If you are a first-time contributor, a maintainer may need to click
  **Approve and run** before the first workflow execution. Subsequent pushes
  to the same PR run automatically.
- The `publish.yml` workflow does **not** run on PRs; it only fires on tagged
  releases from `main`.
- Maintainer will rebase and merge once the review is green and CI passes;
  the branch is deleted after merge.

## Keeping your fork up to date

Rebase rather than merge to keep history linear:

```bash
git fetch upstream
git rebase upstream/main
git push --force-with-lease
```

## Reporting bugs and proposing features

Open a GitHub issue before starting on large changes so we can discuss scope.
For security issues, please avoid filing a public issue — contact the
maintainer directly.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License, Version 2.0](LICENSE) that covers the project.
