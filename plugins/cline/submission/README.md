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
- the clean-profile Cline lifecycle remains a separate host-acceptance gate
  because the `cline` command is not installed on this machine;
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
