# Git and pull requests

Inspect status, the intended diff, bounded recent subjects, and configured commit/PR templates. Explicit user wording and formats take priority, then project conventions; use these defaults where neither applies.

## Titles and messages

- Commit subject: one short imperative line naming the concrete change. Default to `type(scope): summary`, omitting an unnecessary scope; for example, `fix: preserve query strings in redirects`. Avoid vague subjects and trailing periods.
- Commit body: explain why and any behavior, compatibility, or validation detail the subject cannot convey. A simple change may need only the subject. Do not narrate tool activity or repeat the diff.
- PR title: summarize the final change as a whole. Description: lead with the problem and resulting behavior, then relevant checks and material risks or limits. Preserve required template sections; scale detail to the change. Report actual validation results and label checks not run; planned or pending checks are not successes.

## Attribution and publication

Preserve configured Git identity and genuine human `Co-authored-by` and `Signed-off-by` trailers. Never invent contributors or substitute an AI/bot identity. Omit AI co-author trailers and generated-by credits, including template/history copies. Required factual AI-use disclosures remain truthful; they are distinct from authorship credits. Leave existing history intact. Report missing identity before committing.

Text drafts stay read-only; creating a remote draft PR is a write. Staging, committing, pushing, and creating/editing PRs retain their existing authorization. Before an authorized commit, review the intended staged diff and run relevant checks. Before publishing, check the destination, final diff, title, body, and attribution. Verify the resulting commit, remote ref, or PR content before claiming that step succeeded.
