# 1. Task breakdown and effort

## Outcome

One platform repository holds the promotion policy and the reusable workflows. Sixteen tenant repositories, PSE first, can only move code along the official routes. The three rulesets on each repository are created by one script, so nobody configures 48 screens by hand.

## Work packages

Estimates are person-days for a platform engineer, with architect review on the policy, the pilot, and the client walkthrough. One day is one person for one day.

| ID | Work package | What "done" looks like | Days |
| --- | --- | --- | --- |
| WP1 | Confirm the matrix and the branch names | Written decision: `main`, `uat`, `<tenant>-uat`, `prod`, `<tenant>`, sandbox is everything else | 1.0 |
| WP2 | Policy engine and route tests | `evaluate()` returns the client's sentence and exit 0 or 1 for every official route | 2.0 |
| WP3 | Workflows: policy, build and publish, UAT, production | Reusable workflows. UAT and production do not compile | 3.0 |
| WP4 | Ruleset model and idempotent REST script | Three payloads per tenant. A second run reports unchanged. A drifted review count reports update | 2.5 |
| WP5 | Tenant caller renderer | Each tenant repo gets generated callers. Branch lists come from the same spec as the rulesets | 1.0 |
| WP6 | Contract tests | A change that points a workflow at a branch the ruleset does not protect fails CI | 1.5 |
| WP7 | Pilot on PSE in this GitHub account | Seven pull requests show the allowed and blocked routes. Rulesets are active | 1.5 |
| WP8 | Roll out the other 15 repositories | Inventory of 16. `--check` exits 0. One drift injected on purpose is detected | 2.0 |
| WP9 | Runbook, break-glass, and the client walkthrough | Operators know the rollout order and how a named admin bypass would be added later | 1.5 |
| | Engineering subtotal | | **16.0** |
| | Contingency | Check-name confirmation, token scope, private-repo access, GitHub API validation | **3.0** |
| | **Planned total** | | **19.0** |

## Calendar

| Staffing | Calendar |
| --- | --- |
| One platform engineer, architect reviews WP1, WP7, and WP9 | 3 weeks |
| One person doing the engineering and the architecture | 4 weeks |

Week 1 is the matrix, the policy, and the workflows. Week 2 is the ruleset script, the contract tests, and the PSE pilot. Week 3 is the other 15 repositories, a drift check, and the handover. The 3-day contingency sits in week 3 because that is when real tokens and real repository permissions show up.

## The shorter plan

19 days is the from-scratch plan, with slack for access delays. It is not the time left after this submission.

The policy, the four workflows, the ruleset script, the tenant renderer, and the 26 tests are already in this repository. That is the bulk of WP2 through WP6. What remains is turning the rulesets on and pointing them at real repositories.

| Plan | What it includes | Time |
| --- | --- | --- |
| Full, from nothing | Build plus rollout plus 3 days of contingency | 19 days, 3 weeks |
| From nothing, tight | Same build, simulated registry, contingency cut to 2 days | 10 days, 2 weeks |
| After this submission | Rulesets on PSE, then the same script on the other 15 repositories | 3 days |

The 3 days left break down like this:

| Remaining step | Time |
| --- | --- |
| Push this repository, create the PSE branches, apply the 3 rulesets, open the 7 demo pull requests | 2 hours |
| Read the real check name on the first pull request and re-apply if GitHub prefixes it | 0.5 day |
| Receive the 16 repository names and an admin token, then run `--apply` | 0.5 day |
| Open one allowed and one blocked pull request on a sample of tenants and fix anything that fails | 1 day |
| Walk the client through the result | 0.5 day |

A real Artifact Registry connection stays out of these 3 days. It is about 2 extra days once the cloud project and OIDC trust exist. An Enterprise rule that pins the workflow file is also later. Cutting either of those does not weaken the route enforcement.

What I would not remove to save time: the Python allow-or-block check, the ruleset that makes that check mandatory, and the rule that UAT and production reuse the same package. Without those three, the matrix is only a document.

## What this repository already is

WP2, WP3, WP4, WP5, and WP6 are implemented here and covered by the test suite. WP7 is a 2-hour exercise on your own account: push the repository, create the branches, apply the three rulesets, open the seven pull requests. WP8 starts when the client names the other 15 repositories. The script does not change between tenant 1 and tenant 16. The inventory file gains one line per tenant.

## Why the manual alternative costs more

Each repository needs three rulesets: integration, UAT, and production. Sixteen repositories means 48 ruleset screens. Each screen has branch patterns, review count, status checks, force-push, and deletion. A hand edit on tenant 9 is invisible until a feature branch reaches production. The script makes "what is enforced" a reviewable diff in this repository. Re-running it is how drift is repaired.

## Decisions already made

These are the assumptions inside the 19 days. Each one is a constant in `policy/rulesets.py` or `policy/branches.py`, so a client change is a pull request, not a new estimate, unless they add a new environment.

| Decision | Default in this design | If the client wants something else |
| --- | --- | --- |
| Review count | 1 on `main`, 1 on UAT, 2 on production | Change `REVIEW_COUNTS`. About an hour, then re-apply |
| Approvals | Production also requires that the latest push is approved | Same file, `require_last_push_approval` |
| Bypass | No bypass actors | Add a named team later. It is an explicit payload change |
| Sandbox | Any source may enter a non-governed branch | The client matrix names feature branches. Allowing `main` into `pse-dev` has no promotion power |
| Registry | Simulated URI, real digest identity | Swapping in Google Artifact Registry, GHCR, or ECR is a change inside the publish and promote steps. The gate stays. Budget 2 extra days once the cloud project and OIDC trust exist |
| Account for the demo | Your GitHub account, one public pilot repository | The client's 16 repositories are WP8 |

## What I would not spend days on

I would not build a custom merge bot. GitHub already blocks the merge when a required check fails. I would not click through rulesets to prove the script. I would not fork the policy into each tenant. A tenant file only names the tenant and the branches.

## Rollout order inside WP7 and WP8

This order is part of the estimate because getting it wrong creates a pending check that nobody can satisfy.

1. Merge the workflows to the default branch.
2. Open one pull request and read the check name GitHub actually reports.
3. Apply the rulesets only after that name matches the payload.
4. Repeat per tenant. On GitHub Enterprise, start with enforcement `evaluate`, then switch to `active`.

## Risks that the contingency is for

| Risk | What we do |
| --- | --- |
| The ruleset is turned on before the workflow exists on `main` | The required check stays pending and every pull request freezes. Rollout order above |
| Reusable-workflow check names gain a prefix | The builder has `local` and `reusable` styles. Confirm on the PSE pilot, then apply the style that matches the UI |
| A free personal account cannot put rulesets on a private repo | Pilot repository is public, or the account has GitHub Pro |
| The token cannot administer rulesets | Fine-grained token, Administration: Read and write, on that repository only |
| A tenant renames a job and the check no longer matches | The pull request cannot merge, because the required check never arrives. Fail closed |
