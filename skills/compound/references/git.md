# Git and pull requests

Inspect status, the intended diff, a few recent subjects, and any configured commit template. Explicit user wording and formats win, then project conventions, then these defaults.

- Commit subject: one short imperative line naming the concrete change, by default `type(scope): summary` with an optional scope, e.g. `fix: preserve query strings in redirects`; nothing vague, no trailing period.
- Commit body: why, plus behavior, compatibility, or validation detail the subject cannot carry; a simple change may need none. Do not narrate tool activity or repeat the diff.
- PR: the title summarizes the final change. Find and read the repository's PR template and draft into its headings; without one, lead with the problem and resulting behavior, then completed checks with results, then material risks or limits. List project-documented unavailable or pending checks as `Not run: <check — reason>`.

Preserve the configured author and committer; apply a user identity override only when its stated scope matches the task, which a remote owner or login alone does not establish. Keep genuine human `Co-authored-by` and `Signed-off-by` trailers; never invent contributors or use an AI or bot identity. Omit AI co-author trailers and generated-by credits, including copies from templates or history; required factual AI-use disclosures stay truthful and are not credits. Leave existing history intact. Report missing identity before committing.

Text drafts are read-only; creating a remote draft PR is a write. Staging, committing, pushing, and PR changes keep their existing authorization. Before an authorized commit, review the staged diff and run relevant checks. Before publishing, check the destination, final diff, title, body against the template, and attribution. Verify the resulting commit, remote ref, or PR before claiming success.
