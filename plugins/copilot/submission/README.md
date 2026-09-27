# Copilot default-marketplace refresh

These artifacts refresh draft
[`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56)
without copying Vardoger into the upstream repository. The marketplace entry
continues to reference `dstrupl/vardoger:plugins/copilot`, whose package now has
the Agent Plugins 1.0 root `plugin.json` required by current Copilot CLI.

## Read-only status snapshot

Checked 2026-09-27:

- PR head: `cb52ab8a8b9f2a5bf217b089d3e75add42ce558f`
- current upstream `main`: `fbf7c536a5c7af0c94ff5f528a39004c55129e6d`
- state: open draft, `CONFLICTING` / `DIRTY`, no comments, reviews, or checks
- conflict scope: both files in the PR changed upstream since its original base
- current upstream contribution contract: focused pull request, tests and
  linters passing, clear commit message

Treat the commit IDs as evidence for this refresh, not permanent pins. Fetch
again immediately before rebasing.

## Prepared artifacts

- [`marketplace-entry.json`](./marketplace-entry.json) is the exact object to
  add once to upstream `.github/plugin/marketplace.json`.
- [`README_ENTRY.md`](./README_ENTRY.md) is the exact discovery line to add to
  upstream README's **External Plugins** list.
- [`PR_BODY.md`](./PR_BODY.md) replaces the stale draft body after every listed
  check is true.

The entry's version is intentionally checked against this repository's
portable and compatibility manifests by the local test suite. Update all of
them together for a release.

## Rebase and conflict-resolution plan

Use the existing owner fork and branch. The following changes branch history
and therefore remains an owner action:

```bash
git remote add upstream https://github.com/github/copilot-plugins.git  # if absent
git fetch upstream main
git fetch origin add-vardoger
git switch add-vardoger
git rebase upstream/main
```

The old commit is expected to conflict in `.github/plugin/marketplace.json`
and `README.md`. During conflict resolution:

1. Restore both files from the freshly fetched `upstream/main` so no upstream
   catalog additions or removals are resurrected.
2. Append the one object from `marketplace-entry.json` to the `plugins` array,
   preserving valid JSON and ensuring no other `vardoger` entry exists.
3. Add the one line from `README_ENTRY.md` to the External Plugins list.
4. Stage only those two files and continue the rebase.

Abort with `git rebase --abort` if the resulting diff is not focused. Do not
resolve the marketplace conflict by accepting the old PR copy of the whole
array; that would revert upstream catalog maintenance.

## Validation before any push

```bash
jq -e '.plugins | map(select(.name == "vardoger")) | length == 1' \
  .github/plugin/marketplace.json
git diff --check upstream/main...HEAD
git diff --name-only upstream/main...HEAD
```

The last command must print only:

```text
.github/plugin/marketplace.json
README.md
```

Then compare the inserted object to `marketplace-entry.json`, confirm the
upstream compatibility symlink still resolves, and install the source package
with a clean profile using a current Copilot CLI:

```bash
copilot plugin install dstrupl/vardoger:plugins/copilot
copilot plugin list --json
```

This machine currently has Copilot CLI 0.0.343, which predates plugin-management
commands; it cannot provide current clean-profile acceptance evidence. Upgrade
Copilot CLI before recording that check as passed.

## Owner gates

Do not force-push until the compatibility release is present on public `main`
and the clean-profile install succeeds. After reviewing the focused diff, the
owner may push with `git push --force-with-lease origin add-vardoger`, replace
the PR body, wait for mergeability/checks, and only then mark the draft ready.
Each of those steps is an external write and needs explicit approval.
