---
type: deployment-guide
title: Security Checklist for Public Distribution
created: 2026-04-24
---

# Security Checklist for Public Distribution

Before deploying this repo publicly (GitHub, GitLab, etc.), verify that no personal information or credentials are exposed.

---

## ✅ Code Review Checklist

- [ ] All Python scripts use `os.getenv()` for paths (no hardcoded `C:\Users\...` or `/home/user/...`)
- [ ] `batch_extract.py` reads `ZOTERO_DIR` from environment
- [ ] `notes_ingest.py` reads `OBSIDIAN_VAULT` from environment
- [ ] `zotero_feedback.py` reads `ZOTERO_API_BASE` from environment
- [ ] `start_watcher.bat` auto-detects paths (no hardcoded usernames)
- [ ] No `.env` file is committed (check `.gitignore`)

Run this search to verify:
```bash
grep -r "C:\\Users\|D:\\Obsidian\|D:\\Zotero\|admin\|user\|/home/" _scripts/
grep -r "127.0.0.1:23119" _scripts/  # Should be in environment vars only
```

Expected result: **No matches** (or only in docs/comments).

---

## ✅ Documentation Review Checklist

**CLAUDE.md:**
- [ ] No mention of supervisor names, institution names, or specific project titles
- [ ] No specific sample counts, cohort descriptions, or research status
- [ ] No timelines, deadlines, or paused-project dates
- [ ] Reference genome/tool choices are generic or lab-convention descriptions

**README.md:**
- [ ] No hardcoded paths
- [ ] All examples use environment variables (`$ZOTERO_DIR`, `~/Obsidian`)
- [ ] No personal names or institution references

**SETUP.md:**
- [ ] No hardcoded usernames (replace `C:\Users\{your-username}\` with placeholders)
- [ ] All paths use placeholders: `{ZOTERO_DIR}`, `{OBSIDIAN_ROOT}`, `{USERNAME}` or environment variables

**config.example.yaml:**
- [ ] All paths are placeholders or defaults: `~/Zotero`, `~/Obsidian`
- [ ] No actual API keys, tokens, or credentials

---

## ✅ File Structure Review Checklist

**Excluded from repo (checked in `.gitignore`):**
- [ ] `papers/` — your extracted PDF texts
- [ ] `sources/` — your synthesized research notes
- [ ] `wiki/` — your concept pages and knowledge base
- [ ] `notes/` — your mirrored Obsidian notes
- [ ] `documents/` — your reference materials
- [ ] `config.yaml` — your local configuration
- [ ] `.env` — environment variables
- [ ] `_scripts/_queue/` — transient dispatch files
- [ ] `index.md` — your research index

**Included in repo:**
- [ ] `_scripts/*.py` — scripts with no hardcoded paths
- [ ] `_templates/` — templates (generic, no personal data)
- [ ] `CLAUDE.md` — rules (generalized, no details)
- [ ] `README.md` — documentation
- [ ] `config.example.yaml` — example config
- [ ] `.gitignore` — exclusion rules
- [ ] This checklist and security docs

---

## ✅ Deployment Verification

Before pushing to GitHub:

```bash
# 1. Check no large data files are staged
git status | grep -E "papers/|sources/|wiki/|notes/"
# Expected: No output (should all be in .gitignore)

# 2. Check for hardcoded paths in code
git diff --cached _scripts/ | grep -i "C:\\\|/home/\|D:\\Zotero"
# Expected: No output

# 3. Verify .gitignore is correct
cat .gitignore | grep "papers/\|sources/\|wiki/\|notes/\|config.yaml"
# Expected: All these should be listed

# 4. Check commit size
git log --oneline --reverse | head -1  # Show first commit size
# Expected: < 1 MB (no research data embedded)

# 5. Lint scripts for credentials
grep -r "api_key\|password\|secret" .
grep -r "https://.*@" .
# Expected: No output
```

---

## ✅ Final Security Steps

1. **Create a GitHub repo** and set to **Public**.

2. **Add a SECURITY.md** at repo root (optional but recommended):

```markdown
# Security Policy

## Reporting Vulnerabilities

If you find a vulnerability in the scripts (e.g., SQL injection, code execution),
please report privately to [email] rather than opening a public issue.

## Known Limitations

- **Research data** in `papers/`, `sources/`, `wiki/` is not included in this repo.
  Users must populate these via their own Zotero library and Obsidian notes.
- **Local API assumptions:** Scripts assume Zotero runs on localhost:23119.
  Adjust via environment variables if your setup differs.
```

3. **Add a CONTRIBUTING.md** (optional):

```markdown
# Contributing

This project is primarily a personal knowledge wiki system. Contributions welcome:

- Bug fixes in scripts
- Improved templates
- Documentation corrections
- Configuration examples from other platforms

Please avoid:
- Adding personal research data or notes
- Hardcoding paths specific to your machine
```

4. **Do NOT commit:**
   - Your actual `papers/`, `sources/`, `wiki/`, `notes/`
   - Your personal `config.yaml` (users copy from `config.example.yaml`)
   - Any `.env` files with credentials

---

## ✅ Post-Deployment Checklist

After pushing to GitHub:

- [ ] Verify repo is public and cloneable:
  ```bash
  cd /tmp
  git clone <repo-url> test-repo
  cd test-repo
  ls -la
  ```
  Should have: `_scripts/`, `_templates/`, `README.md`, `CLAUDE.md`, `.gitignore`
  Should NOT have: `papers/`, `sources/`, `wiki/`, `notes/`, `config.yaml`

- [ ] Test setup instructions work for a new user:
  ```bash
  python _scripts/batch_extract.py --help
  # Should work with sensible defaults (paths from environment vars)
  ```

- [ ] Verify no large commits:
  ```bash
  git rev-list --all --object-size --disk-size-delta | sort -n | tail -5
  # Should all be < 1 MB
  ```

---

## ⚠️ If You Accidentally Committed Data

If you realize sensitive data was pushed:

### Option 1: Remove from history (recommended)

```bash
# Remove papers/, sources/, wiki/ from all commits
git filter-repo --path papers --invert-paths
git filter-repo --path sources --invert-paths
git filter-repo --path wiki --invert-paths

# Force-push to GitHub
git push origin --force-with-lease
```

### Option 2: Mark as private and request takedown

If the data is already public:
1. Set repo to private immediately
2. Contact GitHub support
3. Rewrite history and make public again

### Option 3: Force-push with a clean history

```bash
# Create a new clean branch
git checkout --orphan clean-slate
git add _scripts _templates *.md .gitignore config.example.yaml
git commit -m "Clean slate: scripts and templates only"
git push origin clean-slate
git push origin --delete main
git branch -m clean-slate main
git push origin main
```

---

## 🔐 Ongoing Security

- **Review CLAUDE.md every release** for any added project details
- **Update SETUP.md** if deployment paths change
- **Test new scripts** for hardcoded paths before committing:
  ```bash
  python _scripts/new_script.py --dry-run
  ```
- **Monitor `.gitignore`** — add new personal folders as you create them
- **Use a pre-commit hook** to catch commits with `C:\Users` or similar:

  ```bash
  # .git/hooks/pre-commit
  #!/bin/bash
  git diff --cached | grep -i "C:\\Users\|/home/" && echo "Hardcoded paths detected!" && exit 1
  exit 0
  ```

  Make executable:
  ```bash
  chmod +x .git/hooks/pre-commit
  ```

---

## ✅ All Clear?

If you've checked all boxes above, your repo is **safe to publish**. 

Push to GitHub and share freely!
