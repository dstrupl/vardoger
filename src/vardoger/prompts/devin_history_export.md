## Devin history prerequisite

Vardoger reads only Devin CLI's documented, user-enabled ATIF exports. It
does not inspect Devin Desktop or Devin CLI private session storage.

Before a session you want Vardoger to learn from, start Devin CLI with an
explicit export path prepared by `vardoger setup devin`:

```bash
devin --export ~/.vardoger/imports/devin/<session-name>.json -- <prompt>
```

The export is refreshed after each turn. If `vardoger prepare --platform
devin` reports zero conversations, explain this opt-in prerequisite instead
of looking for undocumented history files.
