# Manual marketplace submission runbook

Last verified: **2026-09-27**

This is the owner-facing execution plan for actions that require a browser
login, attestation, license decision, force-push, or upstream review. It does
not authorize any external write by itself. Review the prepared change and
obtain explicit owner approval immediately before each submission or PR update.

## Recommended order

1. Clean-profile test the supported Devin Local ATIF export workflow.
2. Monitor the submitted Cline marketplace PR without duplicating the legacy
   issue.
3. Monitor the submitted Cursor recovery and clean-profile test when the host
   application is available.
4. Treat the Codex official-directory submission as lower priority than hosts where
   Vardoger remains clearly differentiated.
5. Keep ClawHub unpublished for current OpenClaw 2.0 until both compatibility
   and licensing are resolved.
6. Monitor the refreshed Docker and Copilot PRs without reposting or pinging.

Claude Code's community entry, the Official MCP Registry, McpMux, PyPI, and
the `awesome-copilot` skill are current and need no owner action.

## Common preflight

- [x] Work from clean public `main` at `f189c2a824b795c1f5985c3f4a6729f2d645e348` or later.
- [x] Confirm the intended release is on PyPI and every manifest carries the
  same version.
- [x] Run `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src/`, and `uv run pytest`.
- [x] Use the GitHub account `dstrupl` for repository submissions.
- [x] Record the submission URL or ID, date, exact source commit, and current
  review state in `MARKETPLACE_STATUS.md` before ending the session.

## 1. Host-compatibility release

Do not submit stale packages to new review queues. The portable packaging and
Claude metadata portions are complete in this working tree. The 0.4.0 version
is a SemVer minor release because it adds public `vardoger profile` commands,
Devin and OpenClaw history integrations, portable plugin packages, and new
global delivery behavior without removing existing contracts. Before
submission:

- validate the Agent Plugins 1.0 root `plugin.json` now present in each Codex,
  Cursor, and Copilot package, retaining host-specific compatibility files;
- verify Cline user-global and legacy `.clinerules` project delivery;
- verify `windsurf` remains clearly labeled as legacy Cascade, while the
  separate `devin` target consumes only explicit `--export` ATIF files and
  writes documented AGENTS/rules/skills paths;
- confirm the Claude custom-marketplace metadata still matches the release;
- verify direct installs for every supported host.

The local release-candidate gate also requires the full repository quality
suite, deterministic Codex archive validation, wheel and sdist inspection, and
installation from the built wheel into a clean temporary environment. These
checks prepare the artifact but do not replace required CI, tagging, GitHub
release, PyPI publication, or clean-profile UI acceptance in each host.

Local evidence captured on 2026-09-27:

- Ruff, formatting, MyPy, rendered-skill consistency, Bandit, and pip-audit
  passed; 389 tests passed with 90.13% combined coverage.
- Twine accepted both `vardoger-0.4.0-py3-none-any.whl` and
  `vardoger-0.4.0.tar.gz`; a clean wheel install resolved MCP 1.30.0 and loaded
  the MCP server as Vardoger 0.4.0.
- All eight `setup` targets passed from the installed wheel, including valid
  0.4.0 OpenClaw frontmatter. The profile compiler completed sources, preview,
  preview-only write, and explicit `--apply` acceptance while preserving
  existing `AGENTS.md` content.
- Record fresh SHA-256 values after the final documentation edit and artifact
  rebuild; do not embed the sdist's own digest in a file included by the sdist.

Release delivery completed on 2026-09-27: PR #37 was rebase merged, main CI
passed, annotated tag `v0.4.0` and the GitHub release are live, and trusted
publishing uploaded the matching wheel (`a364b910...`) and source distribution
(`ad3ddd53...`) to PyPI. Host UI acceptance and separately versioned registry
updates remain independent follow-up gates.

## 2. Cursor Plugin Registry

Current public state: `https://cursor.com/marketplace/vardoger` displays
**Marketplace Plugin Not Found**, despite returning HTTP 200.

The current official schemas have been checked locally. Use the prepared
[listing copy and recovery checklist](plugins/cursor/submission/README.md).

The owner submitted the current publisher application on 2026-09-27 and Cursor
confirmed receipt. Do not submit another duplicate while it is under review.
The remaining work is to test the MCP server and `.mdc` rule lifecycle from a
clean Cursor profile when the host application is available, then verify the
public route in a signed-out browser before marking the row Live.

## 3. GitHub Copilot CLI default marketplace

Current review item: [`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56).
On 2026-09-27 it was rebased onto upstream `fbf7c53`, reduced to the exact
Vardoger marketplace object plus README line, force-pushed with lease, and
marked ready for review. GitHub reports it mergeable and blocked only on
required review.

Copilot CLI 1.0.88 installed the public source package from
`dstrupl/vardoger:plugins/copilot` in a clean temporary profile and listed
Vardoger 0.4.0 as enabled. The refreshed submission head is `226217c`; see the
[recorded evidence](plugins/copilot/submission/README.md). Monitor the PR and
respond to reviewer feedback, but do not repost or ping without a material
change.

## 4. Cline marketplace

Legacy issue [`cline/mcp-marketplace#1394`](https://github.com/cline/mcp-marketplace/issues/1394)
is still open but no longer represents the current intake path. Do not ping,
duplicate, or close it without owner approval.

Current review item: [`cline/marketplace#143`](https://github.com/cline/marketplace/pull/143).
The focused `registry/mcps/vardoger/entry.json` contribution was submitted on
2026-09-27 from commit `536c66c`. Upstream `npm run validate` passed all 204
entries. The local `cline` command is not installed, so clean-profile Cline UI
acceptance remains separate from schema/catalog validation and is disclosed in
the PR. Monitor the PR and respond to reviewer feedback; leave legacy issue
#1394 untouched.

## 5. OpenAI universal Plugins Directory

The custom repository marketplace remains live and is independent of this
submission. Use the current [OpenAI submission guide](https://developers.openai.com/plugins/deploy/submission)
and [plugin packaging guide](https://developers.openai.com/plugins/build/plugins).

1. Confirm the selected OpenAI organization grants **Apps Management: Write**
   and exposes the verified David Strupl developer identity.
2. Run `.venv/bin/python scripts/build-codex-submission.py --check`, build the
   deterministic archive, and inspect its four-file manifest and SHA-256.
3. Re-run exactly five positive and three negative tests from
   `plugins/codex/submission/TEST_CASES.md` using the synthetic fixture.
4. Verify the website, support, privacy, and terms URLs without authentication,
   and confirm the portal accepts a skill whose core local workflow requires
   the separately installed `vardoger` CLI.
5. Create the portal draft, copy the prepared listing material, select the
   verified identity, review all attestations, and submit.
6. After approval, explicitly publish the approved version; approval alone
   does not make it visible in the shared ChatGPT/Codex Plugins Directory.

Repository-side evidence is complete: Codex CLI 0.146.0 clean-installed
Vardoger 0.4.0 from public `main`, and the deterministic four-file archive has
SHA-256 `c193c9c4ee119d4283baf11099c282cc990279c075e8a3cb65289bf33ff6861d`.
The OpenAI individual developer identity is now verified. The portal still
exposes only **With MCP**, not the documented **Skills only** path. Do not use
`With MCP`: Vardoger's MCP server is local stdio and is not a stable public
HTTPS endpoint. The next gate is OpenAI access/support for Skills-only upload;
after that, the remaining reviewer cases, attestations, submission, and
post-approval publication are human/representational actions.

## 6. OpenClaw ClawHub

The public listing at `https://clawhub.ai/dstrupl/vardoger-analyze` currently
shows 0.3.1, security status `Review`, and MIT-0. Current ClawHub documentation
says every published skill is MIT-0 and forbids conflicting per-skill license
terms, while the source skill declares Apache-2.0.

OpenClaw 2.0 history analysis now has an explicit full-read path through the
official Gateway CLI's `sessions.list` and `chat.history` methods. It never
queries SQLite directly or accepts credentials, but the current checkout lacks
a disposable OpenClaw installation for live acceptance. Do not republish a
ClawHub analyzer until that test passes.

Stop for an explicit owner decision:

- If MIT-0 distribution is accepted, prepare a ClawHub-specific artifact with
  no contradictory license metadata, dry-run it, publish the current release,
  and verify the owner-qualified public page.
- If it is not accepted, do not republish; retire or clearly mark the ClawHub
  route unsupported while retaining local OpenClaw installation.

## 7. Docker MCP Registry

[`docker/mcp-registry#2949`](https://github.com/docker/mcp-registry/pull/2949)
remains open, mergeable, and blocked on review. On 2026-09-27 its branch was
rebased onto current upstream and refreshed to the peeled Vardoger 0.4.0 commit
`f189c2a`, with Devin metadata and corrected local-versus-host-model privacy
copy. The one-file YAML diff parses successfully; Go, Task, and Docker are not
installed here, so the previously successful 11-check validation and image
tool discovery were not rerun. The Official MCP Registry already supplies a
live Docker-compatible discovery route. Check this PR only at low frequency;
do not repost or ping without new review feedback or a material upstream
schema change.

## Completion bookkeeping

For every action:

1. Update the at-a-glance row and the dated evidence in
   `MARKETPLACE_STATUS.md`.
2. Update the matching PRD checkbox or blocker.
3. Record runtime installation proof separately from submission, approval,
   publication, and marketplace discoverability.
4. Never call a row Live until a signed-out user can install it from the named
   public surface.
