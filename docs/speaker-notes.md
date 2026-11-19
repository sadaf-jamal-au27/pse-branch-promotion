# Speaker notes

Twelve minutes. The three documents are the leave-behind. This page is what you say. Have a terminal open in the repository, on `make demo` and `make test`, before you start.

## 0:00 — Open

"The estate has one platform repository and 16 tenant repositories. PSE is the first tenant. Code may move from a feature branch to main, from main to UAT, and from UAT to production. Every other route into UAT or production exits 1.

GitHub rulesets can protect the target branch. They cannot say which source branch is allowed to arrive there. So the design has two parts. A policy decides the route. A ruleset makes that decision impossible to skip. One script writes the three rulesets into every repository, instead of 48 manual screens."

Then run:

```bash
make demo
```

Point at TC-06 and TC-12. Those are the two blocked routes the client called out.

## 3:00 — Effort

"Nineteen days is the from-scratch plan with contingency. I am not asking for nineteen days from today. The policy, the workflows, the script, and the tests are already built. What is left is about three days: turn the three rulesets on for PSE, then run the same script for the other fifteen repositories. A real Artifact Registry connection is a later two days, and it is not required for the route enforcement."

If they ask what changes the estimate: a new environment, such as a pre-production stage that is not in the matrix. A different review count does not. It is one constant and a re-apply.

## 6:00 — Solution

"Main is the factory. It lints, compiles, and publishes one digest. UAT deploys that digest. Production promotes that digest. UAT and production do not compile. I can show the same URI from both stages.

There are three rulesets. Main requires one review and the build check. UAT requires one review and the deploy check. Production requires two reviews and the promote check. Nothing in the payload can bypass them. Sandbox branches are simply not listed, which is what makes them free.

An organization-wide wildcard does not work for the production branch, because that branch is named after the tenant. A wildcard would also lock feature branches. So the rulesets are per repository, and they are generated from the same branch spec as the workflows.

The rollout order matters. The workflow lands on main first. One pull request shows the real check name. Then the ruleset goes active. If you turn the ruleset on first, every pull request waits forever for a check that cannot run."

If they ask about a hotfix: "The fix branch merges to main, main deploys to UAT, UAT promotes to production. The production branch can merge back to main. It cannot merge sideways into UAT."

## 9:00 — Tests

"The client's table is the test list. Twenty-six tests cover 21 routes, the digest, the ruleset payload, and the workflow files. The suite is green.

The case I would want a reviewer to look at is feature to pse-uat. Exit 1, and the log uses the client's sentence: changes must merge into main first. The second is main to prod. Exit 1, skipping UAT.

On GitHub I open the same routes as pull requests. I do not need to merge them. A red check is the block. A green check on main still waits for a second person, because the ruleset requires a review and I cannot approve my own pull request. That is the review mandate working."

Run `make test` if the room wants to see it.

## 11:30 — Close

"PSE proves the matrix on one repository. The inventory file is how it becomes 16 repositories without configuration drift. The registry client is simulated, because that is what the exercise asked for. The digest identity is real, and it is the only part that changes when we connect Artifact Registry.

I would like the client to confirm three defaults: one review on main and UAT, two on production, and no bypass actors. Everything else is already the table they sent."

## If they ask

**Why rulesets rather than the older branch-protection API?**
Rulesets are the current object. Bypass is an explicit list, and it is empty here. The same payload shape works as an organization ruleset later. The older API also cannot express the source branch.

**What if the check name in the UI is different?**
The pull request stays pending, so it fails closed. I confirm the name on the PSE pilot, then set `--caller-style` to match. I do not remove the ruleset to unblock people.

**Can an admin push straight to main?**
Not with this payload. There are no bypass actors. A break-glass actor would be a named team, added in a reviewed change to the generator, and GitHub audits the bypass.

**Can a tenant delete the workflow and merge anyway?**
The required check never arrives, so the merge stays blocked. The remaining hole is a job with the same name that exits 0. That change is itself a pull request into main, so it needs a review. On Enterprise I would add a workflow rule that pins the file from the platform repository. That feature is not on a free personal account, so I am not claiming it is in the pilot.

**Why is the registry simulated?**
The task says to simulate lint and publish. The gate, the exit code, and the "same digest" rule are what stop a bad promotion. Pointing publish at a real registry is about two days once OIDC is in place. I would not put a long-lived cloud key in the workflow.

**What about the other 15 tenants?**
One CSV row each: repository, tenant slug, caller style. Then `--apply`. ACME's production branch becomes `acme`. A branch named `pse` inside ACME is sandbox. There is a test for that, TC-18.

**What if GitHub rejects the ruleset JSON?**
`--apply` prints the API body and stops. The usual cause is the token missing Administration permission, or a private repo on a free plan. The generator is one function, so a field the API moves is a one-place fix and a re-apply. Already-applied repositories stay on the previous good payload until that re-apply.

## What not to do in the room

Do not apply rulesets before the branches and the demo commits exist. Direct pushes start failing, and then you cannot set up the UAT diff. Do not merge the demo pull requests. Do not turn review counts down to zero to make a solo merge look easy. The point is that the check and the review are both mandatory.
