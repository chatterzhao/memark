# Worktree And Branch Rules

This repository follows a strict branch-to-worktree mapping.

## Required Layout

- The main worktree at `<repo-root>` must stay on `develop`.
- Any feature branch must use its own dedicated worktree.
- Dogfood branches must use their own dedicated worktree.
- Research branches must use their own dedicated worktree.

## Current Intended Mapping

- Main development baseline:
  - worktree: `<repo-root>`
  - branch: `develop`
- Dogfood runtime:
  - worktree: `<repo-root>-dogfood`
  - branch: `dogfood/runtime`
- Research:
  - worktree: `<repo-root>-research-mempal`
  - branch: `research/mempal-evaluation`

## Operating Rules

- Do not develop directly on `develop`.
- Do not create a feature branch inside the main worktree and keep working there.
- Before making code changes, confirm both the current worktree path and current branch.
- If a new task belongs to a new branch, create a new worktree first, then switch to that branch there.
- Do not mix dogfood runtime artifacts, research notes, and feature implementation in one worktree.

## Recovery Rule

If the main worktree is found on a non-`develop` branch:

1. Preserve any uncommitted work first.
2. Create or reuse a dedicated worktree for that branch.
3. Move the uncommitted work to that dedicated worktree.
4. Switch the main worktree back to `develop`.

## Cleanup Rule

- Stale `prunable` worktree records may be pruned.
- Do not delete active dogfood or research worktrees unless their contents have been intentionally consumed or retired.

## Consumption Rule

- When a feature branch is complete, merge that branch into `develop` from the main worktree while the main worktree is checked out to `develop`.
- Do not keep implementing the same topic on `develop` after a feature worktree already exists for it.
- Before merging, review whether another active worktree has already advanced the same topic; consume the most advanced branch instead of rebuilding the gap from `develop`.
- If a branch is not ready, leave its worktree in place and mark it as still in progress rather than deleting it.

## Retirement Rule

- After a feature branch has been merged and no further isolated work is needed, remove its dedicated worktree with `git worktree remove <path>`.
- Only delete the local branch after confirming it has been consumed by `develop` or otherwise intentionally archived.
- Dogfood and research worktrees are retired only when their operational or research value has been intentionally concluded, not merely because they are unmerged.

## Current Completion State

- `feature/git-hygiene-dogfood` has already been consumed by `develop` and its dedicated worktree has been retired.
- `feature/worktree-governance` has already been consumed by `develop` and its dedicated worktree has been retired.
- `feature/consumption-proof` has already been consumed by `develop` and its dedicated worktree has been retired.
- `feature/runtime-artifact-cleanup` has already been consumed by `develop` and its dedicated worktree has been retired.
