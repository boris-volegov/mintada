# PostgreSQL MCP Server

This directory contains the source code for the PostgreSQL MCP Server, which exposes the Mintada PostgreSQL database via the Model Context Protocol.

## Transport

The server now uses **streamable HTTP MCP** and exposes the MCP endpoint at:

- `http://localhost:8080/mcp-postgres`

## Docker Usage

### Build

From repo root:

```powershell
docker build -t postgres-mcp -f src/Tools/Mintada.Mcp.Postgres/Dockerfile .
```

### Run

Pass the PostgreSQL connection string and publish port `8080`:

```powershell
docker run --rm -p 8080:8080 -e "PG_CONNECTION_STRING=Host=host.docker.internal;Port=5432;Database=mintada_db;Username=admin;Password=mintada" postgres-mcp
```

Optional environment variables:

- `PG_CONNECTION_STRING` (default: `Host=localhost;Port=5432;Database=mintada_db;Username=admin;Password=mintada`)
- `ASPNETCORE_URLS` (default: `http://0.0.0.0:8080`)

## Codex Configuration

Use a URL-based MCP server (no `docker run` spawn per connection):

```toml
[mcp_servers.postgres]
url = "http://localhost:8080/mcp-postgres"
```

## Other MCP Clients

For clients with JSON config:

```json
{
  "mcpServers": {
    "postgres": {
      "url": "http://localhost:8080/mcp-postgres"
    }
  }
}
```
