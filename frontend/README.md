# FounderReach Frontend (`frontend/`)

This folder contains all user interface assets for FounderReach:
- `index.html` — Single-page local client review interface
- `styles.css` — Self-contained dark UI styles (zero external CDNs or tracking fonts)
- `app.js` — Client-side controller

## Boundary Guarantee
In accordance with [CLIENT_BOUNDARY_POLICY.md](../CLIENT_BOUNDARY_POLICY.md):
- The UI operates locally and never collects or stores client credentials, repository tokens, or database secrets.
- Every finding and fix is presented as a **copyable suggestion** for the founder to review and apply on their own site.
