# Prior user feedback

The user has previously edited the generated personalization. Treat these
hints as strong signals when producing the new synthesis:

## Rules the user kept as-is

These have been validated by the user. Prefer phrasing patterns consistent
with them when you write new rules:

{kept_rules}

## Rules the user removed

The user explicitly deleted these rules. Do **not** re-emit them unless you
have materially stronger evidence in the new batch summaries. If you must
include a related observation, re-phrase it.

{removed_rules}

## Rules the user added by hand

The user authored these themselves. Preserve them verbatim in the new
personalization (you may re-categorize them). They take precedence over
anything you would have inferred.

{added_rules}

When in doubt, respect the user's edits over patterns you detect in the
conversation history.
