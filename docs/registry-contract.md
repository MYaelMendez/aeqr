# The æQR registry contract

One registry drives navigation, QR links, and the sitemap. Each entry carries:

- **id** — stable, unique
- **name** — display name
- **path** — source path in the constellation
- **category** — one of the 8 categories
- **scope** — `public` | `local` | `private` | `hybrid`
- **route** — canonical HTTPS URL (public/hybrid) or `ae://local/...` (local/private)
- **type** — page | scene | video | agent | config | log | widget | kanban
- **verified** — has a real check proven this entry resolves?
- **evidence** — pointer to the proof, or null

## Invariants (enforced by `ae.registry.validate`)

- every required field is present
- `scope` is one of the four
- ids are unique
- **public scope ⇒ the route is an HTTPS URL**
- **local scope ⇒ the route is an `ae://local/` scheme address**

## The rule

A registry entry is an **address and a scope**, never a grant. Discovery
(resolve/read/verify) is open; effect (publish/execute/merge) requires an
explicit capability. **A category placeholder is not individual resource
resolution** — each entry resolves to its own canonical route.
