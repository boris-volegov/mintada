---
description: Start a new task by creating a fresh branch from main
---

1. Check git status to ensure the working directory is clean.
   - Run: `git status`
2. Checkout the `main` branch.
   - Run: `git checkout main`
3. Pull the latest changes from the remote.
   - Run: `git pull`
4. Create a new branch for the task.
   - Ask the user for a branch name if one isn't obvious from the context, or generate a descriptive one (e.g., `feature/description-of-task` or `fix/issue-description`).
   - Run: `git checkout -b <branch_name>`
