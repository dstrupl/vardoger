## What

Add Vardoger as an externally hosted Agent Plugins 1.0 package in the default
Copilot plugins marketplace and include it in the external-plugins README
section.

## Why

Vardoger packages a Copilot skill that turns user-selected, locally stored
Copilot CLI conversation history into reviewable user or project instructions.
The open-source CLI has no hosted backend or telemetry. It prepares local
history for analysis by the active Copilot host model, whose data policy still
applies, and preserves instructions outside its managed fenced section.

## User impact

Users can discover and install the `vardoger` plugin while the marketplace
continues to resolve its source from `dstrupl/vardoger:plugins/copilot`.

## Checks

- Parsed `.github/plugin/marketplace.json` and confirmed exactly one Vardoger
  entry.
- Confirmed `.claude-plugin/marketplace.json` resolves to the same manifest.
- Confirmed the source package has an Agent Plugins 1.0 root `plugin.json`, an
  immediate `skills/analyze/SKILL.md`, and matching release versions.
- Installed the source package with a clean, current Copilot CLI profile and
  confirmed the `analyze` skill loads.
- Ran `git diff --check` and verified the final diff contains only the Vardoger
  marketplace entry and README discovery line.
