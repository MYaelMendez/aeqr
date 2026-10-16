# ADR-0002 · Integrate AEEE Lab with æQR (source-grounded)

Status: **integration design; not a deployed adapter**  
Inspected: 2026-10-16

## Sources and existing capabilities

The existing educational/engineering surface is [LutheranInstitute/aeee-lab](https://github.com/LutheranInstitute/aeee-lab/tree/gh-pages), not a replacement for the canonical [MYaelMendez/aeqr](https://github.com/MYaelMendez/aeqr) specification and test repository.

Read source: `AGENTS.md`, `AE-CONTINUITY.md`, `ae-destinations.json`, `skills/ae/SKILL.md`, `skills/ae/references/github-native.md`, and `capability-manifest.json` on `gh-pages`.

Observed:

- `skills/ae/SKILL.md` is a reusable skill for bounded repository operations: **Intent → Inspect → Compose → Execute → Verify → Witness**. Its actual ASCII skill name is `ae`; `$æ` is a semantic/display alias, not proven globally registered.
- `skills/startabusiness/SKILL.md` is a separate business preparation path. Do not require it for ordinary engineering.
- `capability-manifest.json` publishes a discovery index with 22 listed capabilities and access/authority labels. A listed URL or capability is **not** proof that a connected tool is available or authenticated.
- `ae-destinations.json` explicitly keeps **ChatGPT conversation** and the **existing OpenAI-hosted Site** as peer destinations, with optional user-chosen handoff. Its runtime binding is marked **not implemented**.
- `AE-CONTINUITY.md` identifies existing Site, GitHub PR #15, reusable MCP/QR components, and unverified integration boundaries. Its records must be refreshed before deployment.

The supplied URL `https://lutheraninstitute.github.io/aeee-lab/lab/teologia.ai/` could not be fetched through the web reader, and `lab/teologia.ai` is not present in the inspected `gh-pages` tree. **Do not describe that exact page as independently inspected or deployed.** The repository is verified; the specific route is not.

## Shared contracts to implement

1. **Discover:** expose a pinned, versioned, public capability descriptor containing `id`, `version`, `source_repo`, `source_ref`, `artifact_digest`, `hash_domain`, `readable_url`, `skill_url` (optional), `effects`, and `verification`.
2. **Resolve:** æQR resolves that descriptor as **data**. It may offer a readable URL and an optional selected destination; it does not execute a skill or authorize an effect.
3. **Compose:** CodeMode/Codex may read the selected skill's `SKILL.md` and propose an effect-typed plan. Treat remote skill content as untrusted instructions until reviewed and bound to available tools.
4. **Authorize:** independently authenticate the human principal and obtain a task-scoped grant for any effectful operation. A profile, QR, fork, GitHub manifest, or issuer label is never the grant.
5. **Execute:** use an explicitly allowlisted runner (GitHub Actions initially) with least-privilege credentials; correlate commit, workflow, run, and inputs.
6. **Witness:** record observed revisions, input/output digests, checks performed, runner/run identifiers, and unknowns. A source read-back is not a browser test, a successful workflow is not automatically a verified external effect, and a receipt without a signature is not authenticated provenance.

## Integration boundaries

- Preserve the existing OpenAI Site; do not create a replacement Site or plugin.
- Preserve work-in-chat as a complete destination; handoff is **optional**.
- `$ae` is portable skill identity; `æ` is a display glyph. Unicode aliases need host support.
- Do not import credentials, custody secrets, private context, or authority from a fork or QR.
- Use readable labels and URLs alongside symbols; respect reduced motion and mobile accessibility.
- Keep the AEEE Lab as an educational/reference producer, æQR as the canonical transport/verification contract, and CodeMode as a proposed composer, not an automatically trusted executor.

## First measurable vertical slice (proposed, not run)

**Read-only educational artifact discovery**

- Select one public Teologia lesson artifact and pin its source revision.
- Generate a descriptor with **full** SHA-256 and explicit hash domain.
- Resolve it through æQR, show the same ID/revision in the chat and Site where supported.
- Compare decoded QR payloads exactly; verify the selected artifact bytes against the expected digest.
- Return a Witness record identifying what was actually checked.
- Test the skill handoff separately. Do not dispatch a workflow, publish a Site revision, or grant authority during this read-only slice.

## Open questions

- The supplied `/lab/teologia.ai/` route is not visible in the inspected `gh-pages` tree. Is it produced by another branch, external router, or a yet-to-be-published build?
- Which canonical digest domain should be chosen per Teologia artifact: raw bytes or normalized visible text? Both currently exist.
- How will the same public descriptor be consumed by the existing Site and in-chat host without claiming shared sessions?
- What exact signed receipt and issuer trust store should the production Witness verifier accept?

**Invariant:** Many agents. One principal. Context may propagate; authority does not.
