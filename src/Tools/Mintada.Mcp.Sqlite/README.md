# SQLite MCP Server

This directory contains the source code for the SQLite MCP Server, which exposes the Numista coin database via the Model Context Protocol.

## Transport

The server now uses **streamable HTTP MCP** and exposes the MCP endpoint at:

- `http://localhost:8080/mcp-sqlite`

## Docker Usage

### Build

From repo root:

```powershell
docker build -t sqlite-mcp -f src/Tools/Mintada.Mcp.Sqlite/Dockerfile .
```

### Run

Mount the `coins.db` file and publish port `8080`:

```powershell
docker run --rm -p 8080:8080 -v "d:\projects\mintada\data\numista\coins.db:/data/numista/coins.db" sqlite-mcp
```

Optional environment variables:

- `DB_PATH` (default: `/data/numista/coins.db`)
- `ASPNETCORE_URLS` (default: `http://0.0.0.0:8080`)

## Codex Configuration

Use a URL-based MCP server (no `docker run` spawn per connection):

```toml
[mcp_servers.sqlite]
url = "http://localhost:8080/mcp-sqlite"
```

## Other MCP Clients

For clients with JSON config:

```json
{
  "mcpServers": {
    "sqlite": {
      "url": "http://localhost:8080/mcp-sqlite"
    }
  }
}
```
