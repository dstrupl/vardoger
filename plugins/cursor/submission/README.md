# Cursor Marketplace recovery package

This directory holds the owner-facing material used to restore Vardoger's
missing Cursor Marketplace listing. The current recovery application was
submitted on 2026-09-27 and Cursor confirmed receipt.

## Source submitted to Cursor

- Repository: `https://github.com/dstrupl/vardoger`
- Plugin directory: `plugins/cursor`
- Portable manifest: `plugins/cursor/plugin.json`
- Cursor compatibility manifest:
  `plugins/cursor/.cursor-plugin/plugin.json`
- Logo: `plugins/cursor/assets/logo.svg`
- Public slug to restore: `vardoger`

The package deliberately retains both formats supported by Cursor's current
plugin reference. The root Agent Plugins manifest provides portable MCP
packaging; `.cursor-plugin/plugin.json` retains Cursor-specific compatibility
and references the committed logo and `mcp.json`.

## Listing copy

**Name:** Vardoger

**Short description:** Personalize your AI assistant from local conversation
history using the active host model.

**Long description:**

> Vardoger turns conversation history already stored on your machine into
> reviewable working preferences. In Cursor, its MCP workflow prepares local
> history in bounded batches, asks the active Cursor model to synthesize
> recurring preferences, and lets you preview the result before writing it.
> Project-scoped output uses Cursor's current `.cursor/rules/vardoger.mdc`
> format. Vardoger has no hosted backend or telemetry; model-side analysis
> follows your selected model provider's data policy.

**Category:** Productivity

**Keywords:** personalization, productivity, MCP, local-first

**Homepage:** `https://github.com/dstrupl/vardoger`

**Repository:** `https://github.com/dstrupl/vardoger`

**License:** Apache-2.0

**Recovery note, if the form provides a comment field:**

> This submission restores the previously public `vardoger` slug, which now
> displays “Marketplace Plugin Not Found.” The package has been updated to the
> current Agent Plugins root manifest while retaining Cursor's compatibility
> manifest. Please deduplicate this request against the submissions made on
> 2026-04-20 and 2026-05-16.

## Owner preflight and submission gate

- [ ] Publish the compatibility release and confirm all manifests identify
  that released version.
- [ ] Validate both manifests against their current official schemas.
- [ ] Confirm every manifest path is relative and resolves inside
  `plugins/cursor`.
- [ ] From a clean Cursor profile, load the package locally, confirm the
  Vardoger MCP server initializes, and run a synthetic status/prepare/preview
  flow. Copy the package into `~/.cursor/plugins/local`; do not symlink to a
  checkout outside that directory because current Cursor skips such links.
- [ ] Confirm a project write creates `.cursor/rules/vardoger.mdc` with valid
  frontmatter and that rejection restores or removes only Vardoger-owned
  output.
- [ ] Open `https://cursor.com/marketplace/publish` while signed in as the
  owner, accept the current Publisher Terms, and review all generated fields.
- [ ] Obtain explicit owner approval immediately before selecting the final
  submit control.
- [ ] Verify the signed-out public route and record the submission date,
  source commit, acknowledgement, and review state in
  `MARKETPLACE_STATUS.md`.

Cursor's publisher page is a submission form, not a submission-history
dashboard. Do not mark the integration Live until a signed-out visit to
`https://cursor.com/marketplace/vardoger` shows the actual listing rather than
the current not-found page.

## Current submission evidence

On 2026-09-27 the owner submitted as the individual publisher `dstrupl`, using
the public Vardoger repository, the committed Cursor logo, the project website,
and the local-first description above. The success page displayed “Thanks for
applying” and “We've received your submission.” Cursor supplied no public
submission ID or review dashboard, so subsequent verification must use email
from `marketplace-publishing@cursor.com` and the signed-out public route.

## Local validation evidence

On 2026-09-27, the compatibility manifest passed Cursor's Draft 7 schema from
`cursor/plugins` commit `ecc249f1e306fc64ddf83c7bed16cacf7c2239db`.
The root `plugin.json` and `mcp.json` separately passed the official Agent
Plugins 1.0 schemas, and the compatibility manifest's `logo` and `mcpServers`
paths both resolved inside the package. This establishes package/schema
readiness; it does not replace Cursor clean-profile acceptance or marketplace
review.
