# Manual marketplace submission runbook

Last verified: **2026-07-10**

This runbook covers the remaining actions that require a human owner, a
browser login, an attestation, or an upstream review decision. Vardoger 0.3.2
is already released. Do not create duplicate submissions for marketplaces
that are already live or already have an open review item.

## Recommended order

1. Submit the prepared Codex skills-only plugin through the OpenAI Platform.
2. Review the GitHub Copilot default-marketplace PR and mark it ready.
3. Allow Anthropic's automatic pin updater two nightly cycles, then use the
   fallback refresh submission only if the Claude Code catalog is still stale.
4. Monitor the existing Cline and Docker submissions without reposting them.

## Common preflight

- [ ] Work from the public `main` branch at `4fbf0edf30f770babf95781e001d9ec9bbc18b68`
  or a later commit.
- [ ] Confirm the 0.3.2 release commit exists:
  `55a2ca53a1fed872efd510fb1de7631a845f2b12`.
- [ ] Use the GitHub account **`dstrupl`** for every GitHub action.
- [ ] Keep the repository URLs, privacy policy, terms, support URL, and
  publisher identity consistent across all forms.
- [ ] Record the submission URL or ID and submission date before closing a
  portal tab.

## 1. OpenAI universal plugin directory — submit now

This is a new public-directory submission. The existing repository marketplace
under `.agents/plugins/` is a separate distribution route and does not replace
this submission.

Source of truth:

- [OpenAI submission guide](https://developers.openai.com/codex/submit-plugins)
- [Prepared listing material](plugins/codex/submission/README.md)
- [Exactly five positive and three negative tests](plugins/codex/submission/TEST_CASES.md)

### A. Confirm access and publisher identity

1. Open [OpenAI Platform role settings](https://platform.openai.com/settings/organization/people/roles).
2. Select the organization that will own the public plugin.
3. Confirm one of the following:
   - you are an organization owner; or
   - your role has **Apps Management: Write**.
4. Open [organization settings](https://platform.openai.com/settings/organization/general)
   in the same organization.
5. Confirm the individual developer identity for **David Strupl** is verified.
   Complete individual verification if it is not.
6. Keep this organization selected when opening the submission portal. A
   verified identity in one organization is not sufficient when the draft is
   created in another organization.

Stop here if the verified identity is not available in the plugin form. Fix
the organization or role mismatch before creating the submission.

### B. Check the public material

Open each URL in a private browser window and confirm it does not require a
GitHub login:

- Website: `https://github.com/dstrupl/vardoger`
- Support: `https://github.com/dstrupl/vardoger/issues`
- Privacy: `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md`
- Terms: `https://github.com/dstrupl/vardoger/blob/main/TERMS.md`

The production logo is `plugins/codex/assets/logo.png` (400 x 400 PNG).

The portal accepts the final skill directory or a ZIP. If a ZIP is required,
create and inspect it from the repository root:

```bash
(cd plugins/codex/skills && zip -r /tmp/vardoger-codex-analyze-0.3.2.zip analyze)
unzip -l /tmp/vardoger-codex-analyze-0.3.2.zip
```

The archive should contain `analyze/SKILL.md` and no repository submission
notes, test fixtures, `.DS_Store`, or credentials.

### C. Create the draft

1. Open the [OpenAI plugin submission portal](https://platform.openai.com/plugins).
2. Select **Create plugin**.
3. Select **Skills only**.
4. Do not select **With MCP**. This submission packages the Codex skill; it
   has no hosted app, MCP endpoint, authentication, or demo account.

### D. Complete the Info section

Enter these values:

| Field | Value |
|---|---|
| Plugin name | Vardoger |
| Short description | Personalize your assistant from your own conversation history |
| Category | Productivity |
| Developer identity | David Strupl's verified individual identity |
| Website | `https://github.com/dstrupl/vardoger` |
| Support | `https://github.com/dstrupl/vardoger/issues` |
| Privacy policy | `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md` |
| Terms | `https://github.com/dstrupl/vardoger/blob/main/TERMS.md` |
| Logo | `plugins/codex/assets/logo.png` |

Use this long description:

> Vardoger helps Codex adapt to how you actually work. Its skill reads the
> Codex conversation history already stored on your machine, processes it in
> reviewable batches, and synthesizes recurring preferences such as your
> tools, coding conventions, communication style, and workflow boundaries. It
> writes the result into a clearly fenced section of your Codex `AGENTS.md`,
> preserving instructions you wrote yourself. Vardoger has no account,
> telemetry, or hosted backend; the CLI runs locally, and model-side analysis
> stays within the Codex session you are already using.

Before continuing, preview the listing and check that the developer name and
all four public URLs match.

### E. Upload the skill

1. Open the **Skills** section.
2. Upload `plugins/codex/skills/analyze/`, or upload
   `/tmp/vardoger-codex-analyze-0.3.2.zip` if the portal requires an archive.
3. Confirm the portal recognizes `analyze/SKILL.md`.
4. Confirm no scan warning is unresolved before continuing.

Reviewer prerequisite: Python 3.11+ and `vardoger` on `PATH`. The released
package can be installed with:

```bash
pipx install vardoger==0.3.2
```

### F. Add starter prompts

Create these three starter prompts, in this order:

1. `Analyze my Codex history and personalize how you work with me.`
2. `Show what you have learned about my working preferences.`
3. `Refresh my Vardoger personalization from recent conversations.`

### G. Add the tests

1. Open the **Testing** section.
2. Copy the five sections under **Positive test cases** from
   `plugins/codex/submission/TEST_CASES.md`, one case per portal entry.
3. Verify the positive-test counter is exactly **5**.
4. Copy the three sections under **Negative test cases**, one case per portal
   entry.
5. Verify the negative-test counter is exactly **3**.
6. Preserve each case's prompt or scenario, expected behavior, expected result
   shape, fixture data, and safety rationale. Do not combine cases.

The synthetic fixture is public at:

`https://raw.githubusercontent.com/dstrupl/vardoger/main/plugins/codex/submission/fixtures/codex/rollout-review.jsonl`

Mention the fixture URL in any portal field that asks how a reviewer can
reproduce the tests. No account, credentials, private data, or private-network
access is required.

### H. Availability and final submission

1. Open the **Global** section.
2. Select every country and region offered by the portal where this
   open-source developer tool can legally be distributed.
3. Open the **Submit** section and review every tab once more.
4. Use these release notes:

   > Initial submission of Vardoger 0.3.2 as a skills-only plugin. The plugin
   > analyzes local Codex history in batches, synthesizes working preferences,
   > and manages only a fenced Vardoger section in `AGENTS.md`. No account,
   > remote backend, demo credentials, or additional authentication is
   > required.

5. Complete the policy attestations only after confirming that the listing,
   skill, prompts, tests, availability, and data-handling statements are
   accurate.
6. Select **Submit for Review**.
7. Record the plugin or submission ID, submission URL, organization, date,
   and the initial portal status.

### I. After review

Submission does not publish the plugin automatically.

1. Check the portal for reviewer questions; answer with public repository
   evidence and keep any requested change scoped to the Codex skill package.
2. When OpenAI approves the submission, open the approved item and select
   **Publish**.
3. Verify that Vardoger appears in the universal plugin directory in both
   ChatGPT and Codex.
4. Update `MARKETPLACE_STATUS.md` first to **Submitted**, then to **Live**
   after publication. Record the submission/listing URL and dates.
5. Mark the matching `PRD.md` marketplace item complete only after the public
   listing is verifiably live.

## 2. GitHub Copilot default marketplace — mark the PR ready now

Do not open another PR. The submission already exists as draft
[`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56)
from `dstrupl:add-vardoger`.

Live state on 2026-07-10: open draft, no comments, no reviews, no reported
checks, and `REVIEW_REQUIRED`. The draft state is the only intentional blocker.

### A. Owner review

1. Sign in to GitHub as **`dstrupl`**.
2. Open [PR #56](https://github.com/github/copilot-plugins/pull/56).
3. Open **Files changed** and confirm there are exactly two files:
   - `.github/plugin/marketplace.json` — 24 added lines;
   - `README.md` — 2 added lines.
4. In the marketplace entry, confirm:
   - name: `vardoger`;
   - version: `0.3.2`;
   - source repository: `dstrupl/vardoger`;
   - source path: `plugins/copilot`;
   - license: `Apache-2.0`.
5. Confirm the README change only adds Vardoger to the external-plugin
   discovery list.
6. Return to **Conversation** and confirm the title is **Add Vardoger plugin**
   and the description still matches the two-file scope.

### B. Start upstream review

1. Select **Ready for review**.
2. Confirm the yellow draft indicator disappears and the PR remains open.
3. Subscribe to PR notifications if they are not already enabled.
4. Record the date the PR was marked ready in `MARKETPLACE_STATUS.md`.

### C. Handle feedback

1. Respond only to concrete maintainer or automated-review requests.
2. Keep changes on the existing `dstrupl:add-vardoger` branch and retain the
   two-file scope unless a maintainer explicitly asks for more.
3. Re-run the manifest parse, source-path/version check, and
   `git diff --check` after any change.
4. Reply on the existing review thread and resolve it only after the requested
   change is pushed.
5. Do not merge the upstream PR yourself; let the marketplace maintainers
   approve and merge it.

### D. Verify after merge

Use a current Copilot CLI. If `copilot plugin` is missing, update the CLI
before testing.

```bash
copilot plugin marketplace list
copilot plugin marketplace browse copilot-plugins
copilot plugin install vardoger@copilot-plugins
pipx install vardoger==0.3.2
```

Then ask Copilot to analyze the local Copilot CLI history and confirm the
`vardoger` skill is discoverable.

After successful verification:

1. Change the Copilot default-marketplace row in `MARKETPLACE_STATUS.md` to
   **Live**, with the merge commit and date.
2. Update `plugins/copilot/README.md`; replace the current “not yet submitted”
   text with the default-marketplace install command and live status.
3. Update the root `README.md` and `PRD.md` only where their marketplace status
   becomes newly true.

## 3. Claude Code community catalog — wait, verify, then refresh only if needed

Vardoger is already live in the Claude community catalog. This is not a new
listing submission. The catalog currently pins commit
`4831c7a419cf254cbd78690d8f0c52ed6f3def89`, whose plugin version is 0.3.1.

Anthropic's current documentation says approved plugins are automatically
re-pinned as repository commits are pushed, and the public catalog syncs
nightly. The latest Vardoger push happened after the catalog's 2026-07-09 bump
run. Wait through **2026-07-12 morning Europe/Prague time** before using the
fallback form; this allows two complete nightly cycles.

### A. Validate and inspect the automatic update

From the repository root:

```bash
claude plugin validate ./plugins/claude-code
gh api -H 'Accept: application/vnd.github.raw+json' \
  repos/anthropics/claude-plugins-community/contents/.claude-plugin/marketplace.json \
  --jq '.plugins[] | select(.name == "vardoger") | {name, source, homepage}'
```

The validation should pass. The catalog is refreshed when:

- `source.sha` is no longer `4831c7a419cf254cbd78690d8f0c52ed6f3def89`;
- the pinned commit contains version `0.3.2` in
  `plugins/claude-code/.claude-plugin/plugin.json`; and
- the source path remains `plugins/claude-code`.

If the pin is refreshed, do not submit a form. Update the local marketplace
cache and installed plugin instead:

```bash
claude plugin marketplace add anthropics/claude-plugins-community
claude plugin marketplace update claude-community
claude plugin update vardoger@claude-community
```

If the marketplace is already registered, the first command may report that
it already exists; continue with the update commands. Record the new pin and
verification date in `MARKETPLACE_STATUS.md`.

### B. Fallback only if the pin is still stale after 2026-07-12

1. Run the validation and catalog query above once more.
2. Open Anthropic's individual-author
   [Console submission form](https://platform.claude.com/plugins/submit).
   The claude.ai directory form is for Team or Enterprise organizations with
   directory-management access; use it only if that is the intended publisher.
3. If the dashboard offers an existing Vardoger submission, open it and choose
   its update or resubmission action. Prefer this over creating a duplicate.
4. If no update action exists, create exactly one fallback submission using:
   - repository: `https://github.com/dstrupl/vardoger`;
   - plugin root: `plugins/claude-code`;
   - homepage:
     `https://github.com/dstrupl/vardoger/tree/main/plugins/claude-code`;
   - privacy policy:
     `https://github.com/dstrupl/vardoger/blob/main/PRIVACY.md`;
   - platform: Claude Code only;
   - version: 0.3.2;
   - release commit:
     `55a2ca53a1fed872efd510fb1de7631a845f2b12`;
   - current public main commit: the output of `git rev-parse origin/main`
     (`4fbf0edf30f770babf95781e001d9ec9bbc18b68` was the verified baseline
     when this runbook was written).
5. Where the form accepts context, use:

   > Existing approved Vardoger listing refresh. The community catalog remains
   > pinned to 0.3.1 commit 4831c7a after the 0.3.2 release and subsequent
   > pushes. Local `claude plugin validate ./plugins/claude-code` passes.
   > Please refresh the existing listing to the current public `main`; this is
   > not a request for a duplicate listing.

6. Submit once, record the submission ID and date, and do not open a direct PR
   against `anthropics/claude-plugins-community`; that repository is a
   read-only mirror and closes direct submissions.
7. Re-run the catalog query after each nightly sync until the pinned manifest
   reports 0.3.2.

## 4. Existing Cline and Docker submissions — monitor, do not resubmit

These items are already in upstream queues. Check them monthly or when GitHub
sends a notification. A no-change check should not produce a “still waiting”
comment.

### Cline MCP Marketplace

Submission: [`cline/mcp-marketplace#1394`](https://github.com/cline/mcp-marketplace/issues/1394)

Live state on 2026-07-10: open, zero comments, no assignee, last updated
2026-04-25.

1. Open the issue while signed in as `dstrupl`.
2. Check state, assignee, labels, and comments.
3. If nothing changed, close the tab without commenting or opening another
   issue.
4. If a reviewer asks for changes, update the existing issue or the files
   under `plugins/cline/`, reply on the existing thread, and re-test the
   `llms-install.md` flow.
5. Before approval, correct any remaining 0.3.1 wording in the issue body to
   0.3.2. Do not add a separate version-bump comment just to refresh activity.
6. Once accepted, verify the public marketplace installation, then change the
   row in `MARKETPLACE_STATUS.md` to **Live** and update `PRD.md`.

### Docker MCP Registry

Submission: [`docker/mcp-registry#2949`](https://github.com/docker/mcp-registry/pull/2949)

Live state on 2026-07-10: open, not draft, `REVIEW_REQUIRED`, zero comments,
zero reviews, last updated 2026-04-25.

1. Open the PR while signed in as `dstrupl`.
2. Check review requests, comments, merge state, and validation results.
3. If nothing changed, close the tab without pinging maintainers or opening a
   replacement PR.
4. If review restarts, refresh the proposed registry entry from the 0.3.1 pin
   to the peeled 0.3.2 release commit:
   `55a2ca53a1fed872efd510fb1de7631a845f2b12`.
5. Re-run Docker registry validation and the Vardoger tool-discovery build,
   push the focused update to the existing `dstrupl:add-vardoger` branch, and
   reply on the existing PR.
6. After merge, verify the Docker Hub/MCP Toolkit entry and discovered tools,
   then mark the row **Live** in `MARKETPLACE_STATUS.md` and update `PRD.md`.

### ClawHub follow-up

`vardoger-analyze@0.3.2` is already live. There is no submission to repeat.
Before the next Vardoger release, install the packaged skill with the then-
current ClawHub CLI and recheck the previously observed missing-module
regression. Only publish another ClawHub version as part of a real Vardoger
release.

## Repository bookkeeping after any owner action

For every submission, ready-for-review transition, approval, or publication:

1. Update the relevant row and detailed section in `MARKETPLACE_STATUS.md`.
2. Record the exact date, URL or ID, current state, and next check condition.
3. Update a platform README only when user-facing install or availability
   instructions changed.
4. Update the root `README.md` and `PRD.md` only after a public availability
   claim becomes true.
5. Commit documentation updates as a small focused commit and push only after
   verifying the external state.

Use this note format in the status document:

```text
YYYY-MM-DD — <surface>: <action completed>.
Submission/listing: <URL or portal ID>
State: <Draft | Submitted | In review | Approved | Live>
Next check: <date or event>
Evidence: <public URL, commit, or portal status>
```

## No action required now

Do not submit again to PyPI, Cursor, the custom Codex marketplace, the custom
Copilot marketplace, `awesome-copilot`, ClawHub, the Official MCP Registry, or
McpMux. Those routes are already live. Windsurf still has no public third-party
marketplace submission flow; maintain its native skill, CLI, MCP instructions,
and Official MCP Registry route instead.
