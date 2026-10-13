# æQRMode × CodeMode · Reference architecture (proposal v0.1)

**Agentic Electronic Engineering:** translate human intent and physical-digital inputs into authorized computational actions, with reproducible execution and verifiable feedback.

**Canonical upstream:** `MYaelMendez/aeqr`. Fork to retain upstream lineage; use a template for independent projects; clone for a local checkout. **A fork inherits source and contracts, never credentials, grants, or human authority.**

## Components

| Layer | Responsibility | Existing / planned |
|---|---|---|
| æQRMode | Typed addressing, versioned registry resolution, QR supervision | Existing: `ae/envelope.py`, `ae/registry.py`, `ae/supervision.py` |
| CodeMode | Discover typed capabilities; compose a deterministic plan; produce a proposal | **Planned** |
| Policy | Authenticate principal, evaluate scoped grants and required human approvals | Existing illustrative `ae/authority.py`; production enforcement **not yet implemented** |
| Executor | Execute approved, narrowly scoped workflows | Existing read-only `resolve-resource.yml`; effectful executor **planned** |
| Witness | Bind execution ID, inputs, source revision, results, evidence and status | Existing receipts in QR/dispatch flows; generalized execution attestations **planned** |

## Reference lifecycle

```text
ARTIFACT / HUMAN INTENT
  -> æQR RESOLVE (resource ID, immutable commit, trusted digest)
  -> CAPABILITY DISCOVER (typed manifest)
  -> CODEMODE COMPOSE (plan with explicit effects)
  -> POLICY EVALUATE (identity, scope, approval)
  -> EXECUTOR RUN (scoped credentials, isolated runner)
  -> WITNESS RECEIPT (attempted/completed/verified distinguished)
  -> HUMAN REVIEW / FORK / TEACH
```

## Invariants

1. **Discovery != authorization.** QR payloads, repository content, and manifests are untrusted inputs.
2. **Integrity != authenticity.** Verify hashes against a trusted expected digest; use trusted signatures/identity where origin matters.
3. **Plan != effect.** CodeMode proposes; a separate enforcement point authenticates the principal and authorizes effects.
4. **Context may propagate; authority does not.** Never copy grants, tokens or secrets into forks or agent plans.
5. **Workflow success != verified outcome.** Receipts must identify exactly what evidence was checked.
6. **Default deny for side effects.** Read-only discovery may be public; publishing, merging, deployments, payments and external writes need independent authorization.

## Suggested next implementation increments

1. `spec/capability.schema.json`: stable capability ID, input/output JSON schemas, effect classification, executor adapter, provenance and version.
2. `spec/plan.schema.json`: capability DAG, inputs, expected effects, approval requirements, idempotency key.
3. `packages/codemode/`: sandboxed planner that emits plans but cannot access privileged credentials.
4. `packages/adapters/github-actions/`: validate plans and submit only preapproved workflow identifiers, with pinned actions and least-privilege permissions.
5. `spec/receipt.schema.json`: commit SHA, run ID, input digests, approval reference, output digests, status and verification evidence.
6. `templates/teologia/`, `templates/entrepreneur/`: examples without embedded secrets, with accessible no-QR alternatives.

## First demonstrable path

Use **Actions → Resolve æQR resource** for a read-only registry lookup, inspect the JSON report and commit SHA, then manually fork the repository. This demonstrates resolution and reproducible discovery, **not** autonomous CodeMode composition or approved effectful execution.

**æQRMode senses the entry point. CodeMode composes the capability. Human authority governs the effect. Witness closes the loop.**

**Many agents. One principal.**
