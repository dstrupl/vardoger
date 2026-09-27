# Copilot default-marketplace refresh

These artifacts refresh draft
[`github/copilot-plugins#56`](https://github.com/github/copilot-plugins/pull/56)
without copying Vardoger into the upstream repository. The marketplace entry
continues to reference `dstrupl/vardoger:plugins/copilot`, whose package now has
the Agent Plugins 1.0 root `plugin.json` required by current Copilot CLI.

## Submitted status snapshot

Checked 2026-09-27:

- PR head: `226217c42ac68e4169c6919d9a0a06e2e9f7dc8c`
- current upstream `main`: `fbf7c536a5c7af0c94ff5f528a39004c55129e6d`
- state: open, ready for review, mergeable, blocked only on required review
- diff scope: `.github/plugin/marketplace.json` and `README.md` only
- current upstream contribution contract: focused pull request, tests and
  linters passing, clear commit message

Treat the commit IDs as evidence for this refresh, not permanent pins.

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

## Completed rebase and conflict resolution

The existing owner branch was rebased onto current upstream on 2026-09-27:

```bash
git remote add upstream https://github.com/github/copilot-plugins.git  # if absent
git fetch upstream main
git fetch origin add-vardoger
git switch add-vardoger
git rebase upstream/main
```

The old commit conflicted in `.github/plugin/marketplace.json` and `README.md`.
The resolution:

1. Restore both files from the freshly fetched `upstream/main` so no upstream
   catalog additions or removals are resurrected.
2. Append the one object from `marketplace-entry.json` to the `plugins` array,
   preserving valid JSON and ensuring no other `vardoger` entry exists.
3. Add the one line from `README_ENTRY.md` to the External Plugins list.
4. Stage only those two files and continue the rebase.

The resulting focused commit was force-pushed with lease and the PR was marked
ready. Future refreshes must repeat this strategy instead of accepting the old
PR copy of the whole array, which would revert upstream catalog maintenance.

## Validation evidence

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

The inserted object compared exactly to `marketplace-entry.json`, the upstream
compatibility symlink still resolved, and Copilot CLI 1.0.88 installed the
source package with a clean temporary profile:

```bash
copilot plugin install dstrupl/vardoger:plugins/copilot
copilot plugin list --json
```

`copilot plugin list --json` reported Vardoger 0.4.0 installed and enabled.

## Remaining gate

PR #56 now waits for upstream review. Rebase and revalidate only if upstream
changes make it unmergeable or a reviewer requests changes.
