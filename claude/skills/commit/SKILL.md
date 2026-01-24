---
name: commit
description: "look at what is in dirty state with `git status` and :"
---

# Git Commit Skill

look at what is in dirty state with `git status` and :
- ensure that it is not insecure
- ensure it looks correct

Then stage the appropriate files and commit with a proper commit message.

IMPORTANT: Never include "Co-Authored-By" lines in commit messages.

## Files to NEVER commit

Before staging files, always check for and EXCLUDE these patterns:

- **node_modules/** - Never commit node dependencies. If you see thousands of files being staged, stop and check for node_modules.
- **dist/** in node projects that should rebuild - Check if dist is in .gitignore. If the project is a library/CLI that needs dist committed (like MCP servers), it's OK.
- **.env** files - May contain secrets
- **credentials.json**, **secrets.yaml**, etc. - Contains secrets
- **\*.pem**, **\*.key** - Private keys
- **terraform.tfvars** - May contain sensitive infrastructure config

## Warning Signs

If `git status` shows more than ~100 untracked files, investigate before staging:
- Run `git status | grep node_modules` to check
- Run `git status | grep -E "vendor|packages"` for other dependency folders

## Commit Message Style

Follow the project's existing commit style. Common patterns:
- `feat: Add new feature`
- `fix: Fix bug in X`
- `chore: Update dependencies`
- `docs: Update README`

Keep messages concise (1-2 lines for simple changes).
