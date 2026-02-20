# Agent Rules

## Commit Safety

- Never run `git commit` without explicit final user approval in the current thread.
- Before any commit, show:
  - staged file list,
  - short staged diff summary,
  - proposed commit message.
- Stop after showing the above and wait for user confirmation before committing.

## CSS Hard Rules (Non-Negotiable)

- Reuse existing primitives first (for example: `.btn`, `.tab`, `.form-control`, `.brand-divider`).
- Use design tokens only; do not add raw color values in component CSS.
- Add a new CSS class only if no existing primitive can express the requirement.
- Before adding a new class, search existing CSS for reuse candidates.
- Prefer updating `src/Presentation/Mintada.Web/src/index.css` primitives over adding duplicated component-local styles.
