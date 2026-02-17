# Mintada.Api - Summary Documentation

## Overview

`Mintada.Api` is an ASP.NET Core Web API (target `net10.0`) that serves catalog data for issuers and coin types from PostgreSQL via Entity Framework Core (`MintadaDbContext`).

Main responsibilities:

- Return flat issuer lists
- Return hierarchical issuer trees
- Return coin types by issuer id or issuer slug
- Return detailed coin type records including sample images
- Serve static image files from the repository `images` folder for local development

## Tech Stack

- ASP.NET Core Web API
- Entity Framework Core + Npgsql
- OpenAPI endpoint mapping in development
- Project references:
  - `Mintada.Data`
  - `Mintada.Domain`

## Runtime and Configuration

## Database

- Connection string key: `ConnectionStrings:DefaultConnection`
- Development default: PostgreSQL on localhost (`mintada_db`)

## CORS

- Named policy: `AllowFrontend`
- Allowed origin: `http://localhost:5173`
- Allows any method and header

## OpenAPI

- Enabled only in development via `app.MapOpenApi()`

## Static Files

- Default static file middleware is enabled
- Additional image mapping:
  - Local folder: `../../../images` (relative to API content root)
  - URL prefix: `/images`

This is how the web frontend resolves branding and coin sample images.

## Authentication/Authorization

- No authentication configured
- `UseAuthorization()` is present but there are no policies/attributes on controllers

## API Endpoints

## Endpoint Naming Convention

Current standard for this API:

1. Use lowercase paths.
2. Use kebab-case for multi-word segments (for example `coin-types`).
3. Use plural resource names for collections (for example `issuers`).
4. Keep nested resources explicit (for example `/api/issuers/{id}/coin-types`).

## CoinTypesController

Base route: `api/coin-types`

### GET `api/coin-types/{id}`

Returns a single `CoinTypeDetailDto`.

Behavior:

- Query: coin type by exact numeric id
- Includes related samples
- `ObverseImage` and `ReverseImage` shortcut fields are taken from the first sample with `SampleType == 1`
- Returns `404 Not Found` when id does not exist

## IssuersController

Base route: `api/issuers`

### GET `api/issuers`

Returns flat list of `IssuerDto`.

Notes:

- No pagination or filtering currently
- Returns all issuers in one response

### GET `api/issuers/hierarchy`

Returns rooted tree of `IssuerTreeDto`.

Tree building logic:

- Load all issuers into memory
- Build parent-child links by `ParentId`
- Any issuer with missing/unknown parent becomes a root
- Sort roots and all descendants alphabetically by `Name` (case-insensitive)

### GET `api/issuers/{id:int}/coin-types`

Returns list of `CoinTypeDto` for one issuer id.

Notes:

- Route is explicitly constrained to integer ids
- Returns empty list when issuer has no coin types
- Returns `200 OK` (no explicit 404 check for unknown issuer id)

### GET `api/issuers/{slug}/coin-types`

Returns list of `CoinTypeDto` for one issuer slug.

Notes:

- Fallback string route for slug-based lookup
- Integer ids are handled by the `:int` route first
- Returns empty list when slug does not match any issuer

## DTOs

## IssuerDto

- `Id` (int)
- `ParentId` (int?)
- `Url` (string?)
- `Name` (string?)
- `UrlSlug` (string?)
- `TerritoryType` (string?)
- `IsHistoricalPeriod` (bool)
- `IsSection` (bool)

## IssuerTreeDto

- Inherits `IssuerDto`
- Adds `Children: List<IssuerTreeDto>`

## CoinTypeDto

- `Id` (int)
- `IssuerId` (int)
- `Title` (string)
- `Subtitle` (string?)
- `EdgeImage` (string?)
- `Period` (string?)
- `RarityIndex` (int?)
- `CoinTypeSlug` (string)
- `DateTimeInserted` (DateTime)
- `IssueTypeId` (int)
- `ObverseImage` (string?)
- `ReverseImage` (string?)

## CoinTypeDetailDto

- Inherits `CoinTypeDto`
- Adds `Samples: IEnumerable<CoinTypeSampleDto>`

## CoinTypeSampleDto

- `ObverseImage` (string?)
- `ReverseImage` (string?)
- `SampleType` (int)

## Observed Design Decisions and Constraints

1. API shape is catalog-read focused. There are no write/update endpoints yet.
2. Issuer hierarchy is built in application memory rather than with recursive SQL.
3. "Primary" display sample is implicitly defined as `SampleType == 1`.
4. Endpoint behavior is mostly "return empty list" for missing issuer/slug, except coin type detail by id which returns 404.
5. CORS is currently local-development specific (`localhost:5173`).
6. OpenAPI route generation is development-only.

## Suggested Next Steps

1. Add pagination/filtering for large issuer/coin-type datasets.
2. Standardize not-found behavior for issuer coin-type endpoints if required by frontend contracts.
3. Add dedicated endpoints for additional catalog dimensions (for example ruler/shape) to support web `View by` modes.
4. Add API versioning and endpoint contract tests.
