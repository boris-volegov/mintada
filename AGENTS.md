# Agent Rules

## Commit Safety

- Never run `git commit` without explicit final user approval in the current thread.
- Before any commit, show:
  - staged file list,
  - short staged diff summary,
  - proposed commit message.
- Stop after showing the above and wait for user confirmation before committing.
