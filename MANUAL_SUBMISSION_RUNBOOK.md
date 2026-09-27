# Manual marketplace submission runbook

Last verified: **2026-09-27**

This is the owner-facing execution plan for actions that require a browser
login, attestation, license decision, force-push, or upstream review. It does
not authorize any external write by itself. Review the prepared change and
obtain explicit owner approval immediately before each submission or PR update.

## Recommended order

1. Review and publish the prepared 0.4.0 host-compatibility release described
   in PRD Phase 6.
2. Clean-profile test the supported Devin Local ATIF export workflow.
3. Clean-profile test and submit the prepared Cline marketplace PR.
4. Clean-profile test and recover the Cursor listing.
5. Treat Copilot and Codex marketplace work as lower priority than hosts where
   Vardoger remains clearly differentiated.
6. Keep ClawHub unpublished for current OpenClaw 2.0 until both compatibility
   and licensing are resolved.
7. Monitor Docker without reposting or pinging.

Claude Code's community entry, the Official MCP Registry, McpMux, PyPI, and
the `awesome-copilot` skill are current and need no owner action.

## Common preflight

- [ ] Work from a clean, public `main` at or after `f813e9ca00a39371d55994dcfdc75ae6172f26c6`.
- [ ] Confirm the intended release is on PyPI and every manifest carries the
  same version.
- [ ] Run `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src/`, and `uv run pytest`.
- [ ] Use the GitHub account `dstrupl` for repository submissions.
- [ ] Record the submission URL or ID, date, exact source commit, and current
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

The remaining release gate is owner review followed by commit/push, required
CI, an annotated `v0.4.0` tag, GitHub release, and trusted PyPI publication.

## 2. Cursor Plugin Registry

Current public state: `https://cursor.com/marketplace/vardoger` displays
**Marketplace Plugin Not Found**, despite returning HTTP 200.

The current official schemas have been checked locally. Use the prepared
[listing copy and recovery checklist](plugins/cursor/submission/README.md).

1. Publish the compatibility release and confirm the manifest version matches.
2. Test the MCP server and `.mdc` rule lifecycle from a clean Cursor profile.
3. Open `https://cursor.com/marketplace/publish` while signed in as the owner.
4. Submit the current repository and `plugins/cursor` path using the prepared
   listing material. Mention that this restores a previously public slug.
5. Record the source commit and acknowledgement, then verify the public route
   in a signed-out browser before marking the row Live.

## 3. GitHub Copilot CLI default marketplace

Current review item: [`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56).
It is open, draft, `CONFLICTING`, and `DIRTY`, with no reviews or checks.

1. Fetch current upstream and rebase the submission branch.
2. Follow the exact [conflict-resolution kit](plugins/copilot/submission/README.md),
   preserving current upstream files and reapplying only its prepared Vardoger
   marketplace object and README line.
3. Confirm the released source package has the portable Agent Plugins 1.0
   layout, then run the upstream repository's documented validation and inspect
   the final diff for only the Vardoger entry and discovery metadata.
4. Upgrade the local Copilot CLI before clean-profile acceptance; version
   0.0.343 on this machine predates plugin-management commands.
5. Push the rebased branch with lease protection.
6. Recheck mergeability and required checks, then ask the owner to mark the PR
   ready. Do not mark it ready while conflicts or failing checks remain.

## 4. Cline marketplace

Legacy issue [`cline/mcp-marketplace#1394`](https://github.com/cline/mcp-marketplace/issues/1394)
is still open but no longer represents the current intake path. Do not ping,
duplicate, or close it without owner approval.

The current [submission package](plugins/cline/submission/README.md) contains
the upstream-ready `registry/mcps/vardoger/entry.json` and PR body. It passed
upstream `npm run validate` against all 204 entries on 2026-09-27.

1. Publish the compatibility release with Cline global-rule support.
2. Install the rendered command in a clean Cline profile, set
   `VARDOGER_MCP_PLATFORM=cline`, and complete the synthetic lifecycle.
3. Copy the prepared entry into a fresh `cline/marketplace` fork and rerun
   `npm run validate` at the final upstream head.
4. Present the focused diff and prepared PR body for owner approval.
5. After explicit approval, open the PR and record its URL and source commit.

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
remains open, mergeable, blocked on review, and untouched by reviewers. The
Official MCP Registry already supplies a live Docker-compatible discovery
route. Check this PR only at low frequency; do not repost or ping without new
review feedback or a material upstream schema change.

## Completion bookkeeping

For every action:

1. Update the at-a-glance row and the dated evidence in
   `MARKETPLACE_STATUS.md`.
2. Update the matching PRD checkbox or blocker.
3. Record runtime installation proof separately from submission, approval,
   publication, and marketplace discoverability.
4. Never call a row Live until a signed-out user can install it from the named
   public surface.
