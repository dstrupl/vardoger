## What

Add Vardoger as a stdio MCP server in the Cline Marketplace.

Vardoger turns conversation history already stored on the user's machine into
reviewable working preferences. Its MCP workflow uses the active Cline model
for analysis and can write either a dedicated user-global Cline rule or an
explicitly requested project rule.

## Install and safety

The catalog entry installs the published Python package through:

```bash
cline mcp install vardoger -- uvx vardoger mcp
```

`VARDOGER_MCP_PLATFORM` is a required runtime setting and should be set to
`cline`. Vardoger has no hosted backend or telemetry. Local history parsing,
checkpoint state, and rule-file writes run on the user's machine; excerpts
sent to the active model follow that model provider's data policy. Writes are
previewable and restricted to Vardoger-owned output.

## Validation

- [ ] `npm run validate`
- [ ] Clean-profile installation with the rendered command
- [ ] MCP initialization and tool discovery
- [ ] Synthetic analyze, preview, write, and reject/revert flow
- [ ] Public repository, homepage, icon, and license links
