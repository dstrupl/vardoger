# OpenClaw 2.0 history integration decision

Status: opt-in read path implemented; live acceptance and publication gated.

## Supported history contract

OpenClaw 2.0 owns canonical session and transcript state in per-agent SQLite.
Vardoger must not query those tables directly. The supported read path is the
Gateway protocol:

1. Invoke the official `openclaw gateway call` CLI. Vardoger never implements
   the WebSocket handshake, reads a token, or accepts `--url`, `--token`, or
   `--password` options.
2. Let the OpenClaw CLI resolve its configured Gateway and authentication.
   Never create or copy bearer tokens by editing `openclaw.json`.
3. Use only `sessions.list` and `chat.history`. Current Gateways can grant the
   narrow `operator.sessions.read` scope; older supported versions may require
   the broader read-only `operator.read` scope.
4. Page sessions and display-normalized history through those read RPCs.
5. Preserve OpenClaw's session identity and stable `__openclaw.id` anchors;
   never treat numeric offsets as durable checkpoints.
6. Normalize only user and assistant text into Vardoger conversations. Do not
   retain tool payloads, credentials, binary artifacts, or private metadata.
7. Keep Gateway access explicitly opt-in. The current implementation enables
   it only when `VARDOGER_OPENCLAW_GATEWAY=1` and never persists credentials.

## Implemented boundary

Run a full analysis through the supported route with:

```bash
VARDOGER_OPENCLAW_GATEWAY=1 vardoger prepare --platform openclaw --full
```

The implementation shells out without a shell to the installed `openclaw`
binary, requests every visible session, pages each history response, retains
only user/assistant text, and ignores tool and synthetic reset/compaction rows.
It never opens OpenClaw's SQLite or cache databases.

Incremental reads remain disabled. Vardoger's current checkpoint format hashes
files, while Gateway offsets are not stable across compaction or reset. A
future checkpoint migration must persist the stable `__openclaw.id` anchor
with the owning session identity before the default non-`--full` workflow can
be enabled. Remote targets and scope changes remain OpenClaw CLI concerns;
Vardoger does not accept authentication or endpoint overrides.

## Acceptance criteria

- [ ] Works against a disposable OpenClaw profile without direct SQLite access.
- [x] Uses only `sessions.list` and `chat.history` with
  `operator.sessions.read` (or the older broader read-only scope).
- [x] Handles pagination and filters synthetic reset/compaction rows.
- [ ] Persists stable message anchors for incremental reads.
- [x] Produces the same normalized conversation model as other history adapters.
- [ ] Has fixture-based protocol tests plus one human-approved live acceptance
  test against a disposable Gateway.
- [ ] Revoking the paired device prevents future reads without damaging local
  OpenClaw state.

Fixture-backed pagination, filtering, CLI-argument, missing-binary, and config
tests are implemented. The final live acceptance test remains an owner action
because this checkout has no `openclaw` executable or disposable Gateway.

## ClawHub license gate

ClawHub publishes every skill under MIT-0 and does not permit a conflicting
per-skill license override. The repository is Apache-2.0, so the owner must
choose one of these before another ClawHub release:

1. Dual-license only the published OpenClaw skill artifact under MIT-0, remove
   conflicting license metadata from that artifact, and retain Apache-2.0 for
   the rest of Vardoger.
2. Decline MIT-0 distribution and retire or clearly freeze the ClawHub route;
   local OpenClaw installation can remain available under Apache-2.0.

No ClawHub publish or license change should happen implicitly as part of a
general compatibility release.

## Official references

- [Building a Gateway client](https://docs.openclaw.ai/gateway/clients)
- [Query a running Gateway](https://docs.openclaw.ai/cli/gateway/query)
- [Operator scopes](https://docs.openclaw.ai/gateway/operator-scopes)
- [Session state on disk](https://docs.openclaw.ai/reference/session-management-compaction/store)
- [ClawHub skill format](https://docs.openclaw.ai/clawhub/skill-format)
