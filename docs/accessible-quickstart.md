# æQR · Accessible quick start / Inicio accesible

**Scan the artifact. Discover the capability. Verify the provenance. Keep the authority.**

**Escanea el artefacto. Descubre la capacidad. Verifica la procedencia. Conserva la autoridad.**

## No installation required / Sin instalar nada

1. Open the [æQR repository](https://github.com/MYaelMendez/aeqr).
2. Select **Actions** → **Resolve æQR resource** → **Run workflow**.
3. Enter a stable resource ID, for example `html-surfaces-teologia-index`, and select **Run workflow**.
4. Open the run summary and read the **Resolution report**. The workflow also provides a downloadable JSON report.
5. Check the resource's `scope`, `route`, `verified`, and `evidence` fields. A resolved address is **not** proof that the remote resource is reachable or safe.

**En español:** Abre **Actions** → **Resolve æQR resource** → **Run workflow**. Escribe el identificador, ejecuta el flujo y consulta **Resolution report**. Resolver una dirección no concede permisos.

## Access needs / Accesibilidad

- No QR scanner, terminal, GPU, or local Python installation is required for this example.
- All steps can be completed through GitHub's standard web controls, including a keyboard.
- The result is textual Markdown and JSON, not color-only feedback.
- The QR is an optional entry point; always publish a human-readable link and resource ID alongside it.
- For images, provide alternative text; for videos, provide captions/transcripts.
- GitHub account access and repository Actions permissions may be required to manually launch the workflow. Reading existing reports is a separate activity.

## Authority boundary / Límite de autoridad

This workflow **only resolves** an ID in the versioned registry. It does not fetch private resources, execute arbitrary URLs, publish, merge, or mint grants. A scan or resolution is not authorization.

**Context may propagate; authority does not.**

## What the report means

- `found`: the ID exists in this checked-out registry.
- `scope`: public, hybrid, local, or private; do not publish private routes as public links.
- `verified`: a registry claim, **not an independent verification performed by this workflow**.
- `evidence`: the registry's evidence pointer, which may be null.
- `commit`: the Git commit used for this resolution, allowing reproduction.

This is an introductory **discover/resolve** example, not yet a full QR camera-to-execution implementation. Any effectful GitHub Action must use independently validated human authorization and narrowly scoped credentials.
