# Enterprise branch promotion

Live pilot: https://github.com/sadaf-jamal-au27/pse-branch-promotion

PSE is the pilot tenant. The same control then rolls out to the other 15 repositories.

GitHub rulesets can protect a target branch. They cannot say which source branch is allowed to merge into it. This repository is that missing decision, plus the automation that applies it to every tenant without opening 48 ruleset screens.

| Layer | What it does |
| --- | --- |
| Policy | Reads source, target, and tenant. Exits 0 or 1. |
| Workflows | Lint and publish on `main`. Deploy that same digest to UAT. Promote it to production. |
| Rulesets | Make the check, the review, and the "no force-push" rule mandatory. |

The official matrix is already executable:

```bash
make demo
make test
```

`make demo` prints every route. `make test` runs 26 tests. Both passed in this workspace: 21 routes, 0 mismatches.

## What to walk through

1. [Task breakdown and effort](docs/01-task-breakdown-and-effort.md) — 19 days from scratch, about 3 days left after this submission.
2. [High-level solution](docs/02-high-level-solution.md) — the matrix, the three rulesets, the rollout order.
3. [Testing strategy and sample cases](docs/03-testing-strategy.md) — automated cases plus the pull requests to open on your account.
4. [Speaker notes](docs/speaker-notes.md) — a 12-minute script and the questions to expect.

## Repository map

| Path | Role |
| --- | --- |
| `policy/` | Route decision, artifact identity, ruleset payloads, tenant renderer. |
| `.github/workflows/` | Pilot workflows for tenant PSE. They are also the reusable workflows. |
| `templates/tenant-pse/` | The four callers every other tenant repository gets, generated, not hand-copied. |
| `scripts/configure_rulesets.py` | Creates the 3 rulesets per repository. Dry-run unless you pass `--apply`. |
| `src/pse_app/` | The small service the build lints and compiles. |

## Show it on your GitHub account

Use a **public** repository if the account is on the free plan. Repository rulesets on a private personal repo need GitHub Pro. Create a fine-grained token with Administration: Read and write on that repository, and export it as `GH_TOKEN`. The token is only for `--apply`.

Do the branch setup **before** you apply rulesets. After the rulesets are active, direct pushes to `main`, `uat`, `pse-uat`, `prod`, and `pse` are rejected.

```bash
git checkout main
BASE=$(git rev-parse HEAD)

git checkout -B uat "$BASE" && git push -u origin uat
git checkout -B pse-uat "$BASE" && git push -u origin pse-uat
git checkout -B prod "$BASE" && git push -u origin prod
git checkout -B pse "$BASE" && git push -u origin pse
git checkout -B pse-dev "$BASE" && git push -u origin pse-dev

git checkout main
git commit --allow-empty -m "Advance main for the UAT promotion demo"
git push origin main

git checkout pse-uat
git commit --allow-empty -m "UAT validation marker"
git push origin pse-uat

git checkout main
git checkout -B feature/demo-payments
echo "demo change" >> DEMO.txt
git add DEMO.txt
git commit -m "Demo a feature change"
git push -u origin feature/demo-payments
```

Apply the three rulesets for this pilot. `--caller-style local` is required here because these workflows run in this repository. Tenant repositories that call them use `reusable`.

```bash
python3 scripts/configure_rulesets.py \
  --repo OWNER/github-abacus-task \
  --tenant pse \
  --caller-style local \
  --apply
```

Open these pull requests and read the check log. You do not need to merge them. On a personal account you also cannot approve your own pull request, so a green check still waits for a second reviewer. That is the review mandate, and it is what you want to point at.

```bash
gh pr create --base main    --head feature/demo-payments --title "Allow: feature to main"
gh pr create --base pse-uat --head feature/demo-payments --title "Block: feature to UAT"
gh pr create --base prod    --head feature/demo-payments --title "Block: feature to production"
gh pr create --base prod    --head main                 --title "Block: main to prod skips UAT"
gh pr create --base pse-uat --head main                 --title "Allow: main to UAT"
gh pr create --base pse     --head pse-uat              --title "Allow: UAT to production"
gh pr create --base pse-dev --head feature/demo-payments --title "Allow: sandbox"
```

| Pull request | Expected check |
| --- | --- |
| feature → `main` | `promotion-policy` and `build-and-publish` green. An artifact manifest is uploaded. |
| feature → `pse-uat` | Red. Log ends with exit 1 and "must merge into main first". |
| feature → `prod` | Red. Direct feature promotion is blocked. |
| `main` → `prod` | Red. Skipping UAT is blocked. |
| `main` → `pse-uat` | Green. The release record says `compilation: not-performed`. |
| `pse-uat` → `pse` | Green. Same kind of record, promoted to production. |
| feature → `pse-dev` | Green policy, and no UAT or production job runs. |

For the other 15 tenants, add one CSV row each and run the same script. Three rulesets times 16 repositories is 48. The script is the thing that keeps those 48 from drifting.

```bash
python3 scripts/configure_rulesets.py --inventory tenants.example.csv
```

That command is a dry run. Add `--apply` only when `GH_TOKEN` is set and the repository names are real.
