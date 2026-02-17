# Mintada.Web - Summary and Decisions

## What the Website Does

Mintada.Web is the frontend for browsing the Mintada coin catalog.

Current user-facing behavior:

- Landing page with two primary entry points:
  - `Catalog of World Coins`
  - `Manage Your Collection` (placeholder route)
- Catalog browser at `/catalog/issuers`:
  - Hierarchical issuer browsing
  - Issuer detail view with coin type list and sample images
  - Filtering by text
  - Sorting (default / alphabetical)
  - Alphabetical letter jump bar in alphabetical mode

## Data and Integration

- API client is generated from OpenAPI and used by the React app.
- Current backend endpoints used by the catalog are issuer + coin-type focused.
- Ruler and shape-specific catalog APIs are not yet available in the backend, so those views are UI placeholders for now.

## Key Decisions Made

### Catalog "View by" Segmented Control

- Added a segmented control above filter/sort on the catalog summary page.
- Options:
  - `Issuer`
  - `Ruler`
  - `Shape`
- `Issuer` is fully functional.
- `Ruler` and `Shape` currently show placeholder panels pending backend endpoints.

### State and Navigation

- `View by` is URL-driven (`?view=issuer|ruler|shape`) as the single source of truth.
- This avoids local-state synchronization issues and makes behavior link-like/shareable.
- Existing issuer routing (`/catalog/issuers/:issuerSlug`) is preserved.

### Accessibility and Interaction

- Segmented control uses tab semantics (`tablist` / `tab` / `tabpanel`).
- Keyboard navigation supported (`ArrowLeft`, `ArrowRight`, `Home`, `End`).
- Panels remain mounted with `hidden` toggling so `aria-controls` always points to an existing element.

### Mobile Behavior

- Segmented control is horizontally scrollable when space is limited.
- Filter row adapts for narrow screens to avoid overflow.
- Layout remains usable on desktop and mobile widths.

### Visual/Brand Decisions

- Kept icon shapes and style minimal and consistent.
- Brand color decisions:
  - Dark green: `#005c3c`
  - Yellow: `#f5d228`
- Segmented control colors:
  - Inactive text/icons: `#005c3c`
  - Active text/icons: `#f5d228`
  - Active button background: `#005c3c`
- Ruler (crown) icon adjusted:
  - Slightly larger
  - Bottom baseline removed

### Technical Cleanup and Simplification

Applied targeted cleanup in `Mintada.Web` where useful:

- Removed `any`-style metadata plumbing in issuer tree view path and replaced it with typed view nodes.
- Removed dead filtering branches that were not used by the current UI.
- Simplified sort change handling (removed artificial timeout/loading toggle).
- Refactored coin image rendering to reuse helper logic and consistent error handling.
- Removed unused/empty effect in `App.tsx`.
- Cleaned minor encoding/text artifacts and unnecessary comments.

## Known Constraints / Next Steps

- Implement backend endpoints for `Ruler` and `Shape` catalog modes, then wire the frontend placeholders to real data.
- Optional asset cleanup candidates identified as currently unused:
  - `src/assets/images/background_2.png`
  - `src/assets/images/background_3.png`
  - `src/assets/react.svg`
