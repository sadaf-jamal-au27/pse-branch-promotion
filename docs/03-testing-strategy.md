# 3. Testing strategy and sample test cases

## What success means

A route the client marked Allowed merges only when the matching job is green and the reviews are in. A route the client marked Blocked ends in exit 1, and the merge stays disabled. UAT and production ship the digest that `main` published. They do not build a second one. The ruleset on tenant 16 matches the ruleset on PSE, apart from the tenant's own branch names.

## Layers

| Layer | Where it runs | What it proves |
| --- | --- | --- |
| Route unit tests | `make test`, and the `policy-tests` workflow | Every official route, the client sentence, exit code, tenant isolation, case-variant bypass |
| Release tests | Same suite | One SHA, one URI, across publish, UAT, and production. Blocked routes raise before a manifest is written |
| Contract tests | Same suite | Ruleset branch lists, workflow triggers, and rendered callers share one spec. Sandbox is on none of the rulesets |
| Dry run | `make rulesets` | The JSON an operator would send. No token, no network |
| Pilot pull requests | Your GitHub account, tenant PSE | GitHub's UI shows the same allow and block the unit tests show |
| Drift check | `--check` after rollout | A hand edit to one of the 48 rulesets fails the audit |

`policy-tests` is not a required promotion check. The promotion rulesets require `promotion-policy`, `build-and-publish`, `deploy-uat`, and `promote-prod` only. A test workflow must not become a way to block a sandbox experiment, and it must not be something a tenant can satisfy by skipping the real gate.

## Evidence already collected

```text
Ran 26 tests in 0.123s
OK

21 routes, 0 mismatches
```

Blocked feature to UAT, from `python3 -m policy.cli`:

```text
BLOCKED  feature/payments -> pse-uat  uat  reject  exit 1
Rejects direct feature branches. Changes must merge into main first. Route feature/payments -> pse-uat.
```

Same SHA through publish and through production. The URI matches. Production says compilation was not performed:

```text
simulated://artifact-registry/tenants/pse/app@sha256:917e0337b8ad83636d8ac894d6e89e6f19255dc40f47ebb62b16d006262a9da4
```

## Sample automated cases

These are the cases to read out. The full list is `policy/official_matrix.py`, and `tests/test_promotion_policy.py` executes it.

| ID | Route | Tenant | Expected | Assertion |
| --- | --- | --- | --- | --- |
| TC-01 | `feature/payments` → `main` | pse | Allowed, exit 0 | Action `build_and_publish`. Reason is the Artifact Registry sentence |
| TC-02 | `hotfix/tax-round` → `main` | pse | Allowed, exit 0 | "Any branch", not only branches named feature |
| TC-04 | `main` → `pse-uat` | pse | Allowed, exit 0 | Action `deploy_uat` |
| TC-06 | `feature/payments` → `pse-uat` | pse | Blocked, exit 1 | "must merge into main first". Action is `reject`, not `deploy_uat` |
| TC-07 | `pse-dev` → `pse-uat` | pse | Blocked, exit 1 | A sandbox branch is "any other branch" once the target is UAT |
| TC-09 | `pse-uat` → `pse` | pse | Allowed, exit 0 | Action `promote_prod` |
| TC-12 | `main` → `prod` | pse | Blocked, exit 1 | "skipping UAT". This is the route people will try |
| TC-13 | `main` → `pse` | pse | Blocked, exit 1 | The tenant-named production branch has the same rule |
| TC-15 | `feature/payments` → `pse` | pse | Blocked, exit 1 | Direct feature to production |
| TC-16 | `feature/payments` → `pse-dev` | pse | Allowed, exit 0 | Action `sandbox`. No publish |
| TC-18 | `feature/payments` → `pse` | acme | Allowed, exit 0 | Inside ACME, `pse` is not production. Isolation |
| TC-20 | `feature/payments` → `acme` | acme | Blocked, exit 1 | ACME's own production branch still rejects a feature |

### TC-06, written as a test case

| Field | Content |
| --- | --- |
| Title | A feature branch cannot open a pull request into PSE UAT |
| Preconditions | Tenant slug `pse`. Target `pse-uat` is a UAT branch |
| Steps | Run `python3 -m policy.cli --tenant pse --source feature/payments --target pse-uat` |
| Expected | Process exit code 1. Stderr contains `BLOCKED` and `must merge into main first` |
| Automated by | `test_client_sentence_feature_to_uat_exits_1` and `test_cli_exit_codes_match_the_matrix` |
| Failure looks like | Exit 0, or an action of `deploy_uat` |

### TC-12, written as a test case

| Field | Content |
| --- | --- |
| Title | Merging main into production is rejected because UAT was skipped |
| Preconditions | Tenant slug `pse`. Target is `prod` |
| Steps | Evaluate source `main`, target `prod` |
| Expected | Exit 1. Reason contains `skipping UAT` |
| Automated by | `test_client_sentence_skipping_uat_exits_1` |
| Failure looks like | A green `promote_prod` job for a pull request whose head is `main` |

### Digest case

| Field | Content |
| --- | --- |
| Title | UAT and production promote the published digest |
| Steps | `execute("publish", ... sha)`, `execute("uat", ... same sha)`, `execute("prod", ... same sha)` |
| Expected | All three URIs are equal. UAT and production `compilation` is `not-performed`. `publish_main` for that SHA returns the same URI |
| Automated by | `test_the_same_digest_is_promoted_without_recompile` |
| Also guarded by | `test_pilot_workflows_trigger_the_governed_branches` fails if the UAT or production workflow starts calling the linter |

### Ruleset case

| Field | Content |
| --- | --- |
| Title | PSE gets three rulesets and the sandbox branch is not one of them |
| Steps | Build `desired_rulesets("pse", "local")` and plan it twice |
| Expected | Names `enterprise-integration-main`, `enterprise-uat-gate`, `enterprise-production-gate`. Includes are `main`, then `uat` and `pse-uat`, then `prod` and `pse`. Review counts 1, 1, and 2. `bypass_actors` is empty. `pse-dev` does not appear. A second plan against the same payload is `unchanged`. Lowering the production review count in the live object produces `update` |
| Automated by | `test_three_rulesets_and_no_sandbox_branch`, `test_reviews_checks_and_no_bypass`, `test_plan_is_idempotent_and_detects_drift` |

### Extra cases the matrix implied and the tests lock

| Case | Expected | Why it is here |
| --- | --- | --- |
| `pse-uat` → `main` | Allowed, publish | Hotfix and back-merge return through `main` |
| `pse` → `pse-uat` | Blocked, exit 1 | Production cannot step sideways into UAT |
| Target `Main`, `UAT`, `PSE` | Blocked, exit 1 | A case variant must not become an ungoverned sandbox |
| Source `refs/heads/main` | Treated as `main` | GitHub sometimes sends the ref prefix |
| Empty source | Blocked, exit 1 | A push event with no pull request fails closed |
| Lint of `src/` | Pass | The pilot service compiles |
| A file containing `breakpoint()` | Lint fails | The simulated lint is a real reject, not a print statement |

## Sample cases to perform on GitHub

Run these after the rulesets are applied. The steps to create the branches are in the README. Do not merge. The check is the evidence.

| ID | Pull request | Expected on the pull request |
| --- | --- | --- |
| L1 | `feature/demo-payments` → `main` | `promotion-policy` green. `build-and-publish` green. Actions artifact `artifact-registry-<sha>` contains a manifest whose `compilation` is `performed-before-publish` |
| L2 | `feature/demo-payments` → `pse-uat` | `promotion-policy` red. The log line matches TC-06. `deploy-uat` red. Merge disabled |
| L3 | `feature/demo-payments` → `prod` | Red. Direct feature promotion |
| L4 | `main` → `prod` | Red. The log contains `skipping UAT` |
| L5 | `main` → `pse-uat` | Green. Manifest `compilation` is `not-performed` |
| L6 | `pse-uat` → `pse` | Green. Production promotion of the UAT head |
| L7 | `feature/demo-payments` → `pse-dev` | Policy green. `deploy-uat` and `promote-prod` do not run, because the target is not governed |

Two further checks, if there is time:

| ID | Action | Expected |
| --- | --- | --- |
| L8 | `git push origin main` after the ruleset is active | GitHub rejects the direct push. The policy never runs, because the pull-request rule stops it first |
| L9 | Re-run `configure_rulesets.py --check` | Exit 0, three lines of `unchanged`. Edit a review count in the UI, run `--check` again, see `update`, run `--apply`, see `unchanged` again |

## How a failure is handled

| Failed layer | Response |
| --- | --- |
| A unit test goes red | The matrix changed or the engine changed. Do not apply rulesets. Fix the pull request in this repository |
| L2 is green | Stop the rollout. The required check is not the policy, or the workflow is not the one on `main`. Pending checks mean the ruleset name and the job name differ |
| L5 is green but the manifest shows a new compile | The UAT job is rebuilding. Fail the contract test's lint assertion and remove the compile step |
| `--check` reports update on a tenant you did not mean to touch | Someone edited a screen. `--apply` puts the generated payload back. The diff in `--check` is the audit record |
| A tenant pull request is pending forever | The workflow has not run on the default branch yet, or the check context string does not match. This is fail closed. Fix the name, do not delete the ruleset to "unblock" it |

## What I am not calling a test

A screenshot of the ruleset UI is not a test. The test is a pull request whose check exits 1, and a unit test that fails if that exit code changes. The dry-run JSON is the artifact you can read in review. The seven pull requests are the demonstration that GitHub agrees with it.
