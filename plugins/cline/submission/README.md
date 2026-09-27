# Cline marketplace submission package

This directory contains the contribution submitted as
[`cline/marketplace#143`](https://github.com/cline/marketplace/pull/143) to
Cline's current catalog.

## Prepared upstream file

Copy:

```text
registry/mcps/vardoger/entry.json
```

from this directory into the same path in a fresh fork of
`cline/marketplace`. The entry follows the current MCP schema, uses only
canonical tags, leaves `verified` and `featured` false, and renders this
install command:

```bash
cline mcp install vardoger -- uvx vardoger mcp
```

The catalog's `install.env` metadata must prompt for
`VARDOGER_MCP_PLATFORM`; enter `cline`. This preserves Vardoger's
cross-client MCP server while making platform-optional tool calls use Cline
history and Cline rules by default.

## Submission preflight

The catalog contribution was opened after these repository-side gates passed:

- the host-compatibility release is published to PyPI and
  `uvx vardoger mcp` resolves to that release;
- the public homepage, repository, icon, license, privacy policy, and Cline
  instructions are reachable without authentication;
- `npm run validate` passes in a fresh `cline/marketplace` checkout with only
  the prepared `entry.json` added; and
- the focused diff and [`PR_BODY.md`](./PR_BODY.md) had owner approval.

The old `cline/mcp-marketplace#1394` issue belongs to a superseded intake
flow. Do not ping, duplicate, or close it as part of this contribution unless
the owner explicitly chooses to do so.

## Local validation evidence

On 2026-09-27, this entry was copied into a clean snapshot of
`cline/marketplace` at commit
`6969aa8505f2be81bb3627e47ab0037d234aeaf7`. The upstream
`npm run validate` command passed all 204 catalog entries, including
Vardoger. This establishes schema and catalog compatibility; it does not
replace the clean-profile runtime test or upstream review.

The submitted fork commit is `536c66c` on `dstrupl/marketplace:add-vardoger`.
PR #143 is open, mergeable, and awaiting upstream review.

## Runtime acceptance evidence

On 2026-09-27, Cline CLI 3.0.65 accepted the rendered command
`cline mcp install vardoger -- uvx vardoger mcp` and stored the expected stdio
transport plus `VARDOGER_MCP_PLATFORM=cline`. The public Vardoger 0.4.0 package
then completed MCP protocol `2025-06-18` initialization and returned all nine
tools from `tools/list`. The temporary MCP entry was uninstalled after the
test.

This test also found two Cline host defects: the published macOS ARM64 binary
failed macOS validation with `CODESIGNING / Invalid Page` until the temporary,
integrity-checked copy was locally ad-hoc signed, and the MCP installer ignored
the CLI's `--data-dir` isolation flag. Neither defect changes the passing
Vardoger configuration or MCP-runtime result. Marketplace-card click-through
remains unavailable until PR #143 is merged.
