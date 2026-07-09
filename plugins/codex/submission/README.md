# Codex universal directory submission

This directory contains the reviewer-ready material for Vardoger's initial
skills-only submission to the universal plugin directory. It follows the
[OpenAI plugin submission guide](https://developers.openai.com/codex/submit-plugins)
as checked on 2026-07-09.

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
| Short description | Personalize your assistant from your own conversation history |
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

## Skill bundle

Upload `plugins/codex/skills/analyze/` as the final skill directory or ZIP
that directory without adding repository-only submission material. The skill
has no authentication or demo-account requirement. Reviewers need Python
3.11+ and `vardoger` on `PATH`; install the released package with
`pipx install vardoger==0.3.2`.

## Starter prompts

1. Analyze my Codex history and personalize how you work with me.
2. Show what you have learned about my working preferences.
3. Refresh my Vardoger personalization from recent conversations.

## Testing

Use the exactly five positive and three negative cases in
[TEST_CASES.md](./TEST_CASES.md). The synthetic rollout fixture contains no
private or internal data and can be copied into a disposable reviewer's
`~/.codex/sessions/` directory.

## Availability

Select all countries and regions offered by the portal where this open-source
developer tool can legally be distributed. The project provides English
documentation and best-effort support through the public issue tracker.

## Initial release notes

Initial submission of Vardoger 0.3.2 as a skills-only plugin. The plugin
analyzes local Codex history in batches, synthesizes working preferences, and
manages only a fenced Vardoger section in `AGENTS.md`. No account, remote
backend, demo credentials, or additional authentication is required.

## Owner portal checklist

- Confirm the submitting OpenAI Platform organization grants **Apps
  Management: Write**.
- Select David Strupl's verified individual developer identity.
- Confirm the website, support, privacy, and terms URLs resolve from public
  `main`.
- Upload the production logo and the final `analyze` skill directory or ZIP.
- Copy the starter prompts and the eight test cases into the portal.
- Review availability and policy attestations, then submit for review.
