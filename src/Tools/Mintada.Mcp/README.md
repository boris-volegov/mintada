# Mintada MCP Server

This directory contains the source code for the Mintada MCP Server, a tool to expose the Numista coin database via the Model Context Protocol.

## Docker Usage

### Build
To build the Docker image:

```powershell
docker build -t mintada-mcp -f Dockerfile .
```
*(Run from `src/Tools/Mintada.Mcp` directory, or adjust path if running from root)*

**Recommended (from root):**
```powershell
docker build -t mintada-mcp -f src/Tools/Mintada.Mcp/Dockerfile .
```

### Run
To run the server, you must mount the `coins.db` file to `/data/numista/coins.db` inside the container.

```powershell
docker run -i --rm -v "d:\projects\mintada\data\numista\coins.db:/data/numista/coins.db" mintada-mcp
```

## Configuration
To use this with an MCP client (like VS Code or Claude Desktop), add this to your MCP configuration:

```json
{
  "mcpServers": {
    "mintada": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "d:\\projects\\mintada\\data\\numista\\coins.db:/data/numista/coins.db",
        "mintada-mcp"
      ]
    }
  }
}
```
