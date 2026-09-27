# Codex universal directory submission

This directory contains the reviewer-ready material for Vardoger's initial
skills-only submission to the universal plugin directory. It follows the
[OpenAI plugin submission guide](https://developers.openai.com/plugins/deploy/submission)
and [packaging guide](https://developers.openai.com/plugins/build/plugins) as
checked on 2026-09-27.

The repository marketplace under `.agents/plugins/` is already live. This
package is for the separate public directory available in ChatGPT and Codex.

## Submission type

**Skills only.** Vardoger does not submit a hosted MCP server or app. The skill
invokes the locally installed `vardoger` CLI and uses the user's existing
Codex session files.

## Listing information

| Field | Value |
|---|---|
| Plugin name | Vardoger |
| Short description | Personalize from your history |
| Category | Productivity |
| Developer | Select David Strupl's verified individual identity |
| Website | `https://github.com/dstrupl/vardoger` |
| Support | `https://github.com/dstrupl/vardoger/issues` |
| Privacy policy | `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md` |
| Terms | `https://github.com/dstrupl/vardoger/blob/main/TERMS.md` |
| Logo | `plugins/codex/assets/logo.png` (400×400 PNG) |

### Long description

Vardoger helps Codex adapt to how you actually work. Its skill reads the
Codex conversation history already stored on your machine, processes it in
reviewable batches, and synthesizes recurring preferences such as your tools,
coding conventions, communication style, and workflow boundaries. It writes
the result into a clearly fenced section of your Codex `AGENTS.md`, preserving
instructions you wrote yourself. Vardoger has no account, telemetry, or hosted
backend; the CLI runs locally, and model-side analysis stays within the Codex
session you are already using.

## Build and validate the skill bundle

Run the repository-owned validator before creating the upload:

```bash
.venv/bin/python scripts/build-codex-submission.py --check
.venv/bin/python scripts/build-codex-submission.py
```

The second command writes a deterministic archive under `dist/`, with the
version derived from `pyproject.toml`. It contains exactly:

- `plugin.json`, the portable Agent Plugins 1.0 manifest;
- `.codex-plugin/plugin.json`, the OpenAI interface overlay;
- `skills/analyze/SKILL.md`; and
- `assets/logo.png`.

The overlay is required in this package because the portable manifest leaves
OpenAI-specific listing metadata there. The builder excludes this
`submission/` directory, repository caches, and all reviewer fixtures. The
skill has no authentication or demo-account requirement. Reviewers need
Python 3.11+ and `vardoger` on `PATH`; install the same released version named
by the manifest before running the tests.

## Starter prompts

1. Analyze my Codex history and personalize how you work with me.
2. Show what you have learned about my working preferences.
3. Refresh my Vardoger personalization from recent conversations.

## Testing

Use the exactly five positive and three negative cases in
[TEST_CASES.md](./TEST_CASES.md). The synthetic rollout fixture contains no
private or internal data and can be copied into a disposable reviewer's
`~/.codex/sessions/` directory.

## Current build evidence

On 2026-09-27, Codex CLI 0.146.0 added the public `main` marketplace in a
disposable `CODEX_HOME`, installed `vardoger@vardoger`, and listed it as
enabled at version 0.4.0. The deterministic four-file upload archive is
`dist/vardoger-codex-submission-0.4.0.zip`, SHA-256
`c193c9c4ee119d4283baf11099c282cc990279c075e8a3cb65289bf33ff6861d`.
The portal reviewer cases and policy attestations remain human submission
steps rather than repository validation.

On the same date, the OpenAI Platform individual developer identity was
verified successfully. The Plugins portal nevertheless exposed only **With
MCP** in its `Create plugin` menu, both before and after verification; the
documented **Skills only** choice was absent. Do not create a `With MCP` draft
for Vardoger: its MCP server is local stdio, not a public HTTPS endpoint. The
submission is blocked on OpenAI enabling or supporting the Skills-only upload
path for this organization.

## Availability

Select all countries and regions offered by the portal where this open-source
developer tool can legally be distributed. The project provides English
documentation and best-effort support through the public issue tracker.

## Initial release notes

Initial submission of Vardoger 0.4.0 as a skills-only plugin. The plugin
analyzes local Codex history in batches, synthesizes working preferences, and
manages only a fenced Vardoger section in `AGENTS.md`. No account, remote
backend, demo credentials, or additional authentication is required.

## Owner portal checklist

- Confirm the submitting OpenAI Platform organization grants **Apps
  Management: Write**.
- Select David Strupl's verified individual developer identity.
- Confirm the website, support, privacy, and terms URLs resolve from public
  `main`.
- Run `scripts/build-codex-submission.py --check`, build the archive, and
  inspect `unzip -l dist/vardoger-codex-submission-<version>.zip` before upload.
- Upload the deterministic plugin ZIP and provide the production logo
  separately if the portal requests it for listing media.
- Copy the starter prompts and the eight test cases into the portal.
- Review availability and policy attestations, then submit for review.
