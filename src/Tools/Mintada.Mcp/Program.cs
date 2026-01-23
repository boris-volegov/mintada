using System.Text.Json;
using System.Text.Json.Serialization;
using Mintada.Mcp;

// Default to a path that makes sense for the container, but allow override
string dbPath = Environment.GetEnvironmentVariable("DB_PATH") ?? "/data/numista/coins.db";
string connectionString = $"Data Source={dbPath}";

// Using Console.In / Console.Out for stdio transport
var inputStream = Console.OpenStandardInput();
using var reader = new StreamReader(inputStream);
Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });


// Main Loop
while (true)
{
    string? line = await reader.ReadLineAsync();
    if (line == null) break; // End of stream

    try 
    {
        var message = JsonSerializer.Deserialize<JsonRpcMessage>(line);
        if (message == null) continue;

        if (message.Method == "initialize")
        {
            SendResponse(message.Id, new 
            {
                protocolVersion = "2024-11-05",
                capabilities = new 
                {
                    tools = new { }
                },
                serverInfo = new 
                {
                    name = "mintada-mcp",
                    version = "1.0.0"
                }
            });
        }
        else if (message.Method == "notifications/initialized")
        {
            // Valid notification, no response needed
        }
        else if (message.Method == "tools/list")
        {
            SendResponse(message.Id, new 
            {
                tools = new object[]
                {
                    new 
                    {
                        name = "sql_db_list_tables",
                        description = "List all tables in the connected SQL Server database",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new { }
                        }
                    },
                    new 
                    {
                        name = "sql_db_get_table_schema",
                        description = "Get the schema of a table",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new 
                            {
                                tableName = new { type = "string", description = "The name of the table" }
                            },
                            required = new[] { "tableName" }
                        }
                    },
                    new 
                    {
                        name = "sql_db_get_database_info",
                        description = "Get information about the current database",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new { }
                        }
                    },
                     new 
                    {
                        name = "sql_db_get_stored_procedure_definition",
                        description = "Get the definition of a stored procedure",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new 
                            {
                                procedureName = new { type = "string", description = "The name of the procedure" }
                            },
                            required = new[] { "procedureName" }
                        }
                    },
                    new 
                    {
                        name = "sql_db_get_view_definition",
                        description = "Get the definition of a view",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new 
                            {
                                viewName = new { type = "string", description = "The name of the view" }
                            },
                            required = new[] { "viewName" }
                        }
                    },
                    new 
                    {
                        name = "sql_db_execute_query",
                        description = "Execute a SQL query on the connected SQL Server database",
                        inputSchema = new 
                        {
                            type = "object",
                            properties = new 
                            {
                                query = new { type = "string", description = "The SQL query to execute" }
                            },
                            required = new[] { "query" }
                        }
                    }
                }
            });
        }
        else if (message.Method == "tools/call")
        {
            var callParams = JsonSerializer.Deserialize<ToolCallParams>(message.Params?.ToString() ?? "{}");
            string toolName = callParams?.Name ?? "";
            string argsJson = callParams?.Arguments?.ToString() ?? "{}";

            try 
            {
                string resultText = "";
                
                switch (toolName)
                {
                    case "sql_db_list_tables":
                        resultText = SqlDiscoveryTools.ListTables(connectionString);
                        break;
                    case "sql_db_get_table_schema":
                        var schemaArgs = JsonSerializer.Deserialize<Dictionary<string, string>>(argsJson);
                        if (schemaArgs != null && schemaArgs.TryGetValue("tableName", out var tName))
                            resultText = SqlDiscoveryTools.GetTableSchema(connectionString, tName);
                        else 
                            throw new ArgumentException("tableName is required");
                        break;
                    case "sql_db_get_database_info":
                        resultText = SqlDiscoveryTools.GetDatabaseInfo(connectionString);
                        break;
                    case "sql_db_get_stored_procedure_definition":
                        var spArgs = JsonSerializer.Deserialize<Dictionary<string, string>>(argsJson);
                        if (spArgs != null && spArgs.TryGetValue("procedureName", out var pName))
                            resultText = SqlDefinitionTools.GetStoredProcedureDefinition(connectionString, pName);
                        else 
                            throw new ArgumentException("procedureName is required");
                        break;
                    case "sql_db_get_view_definition":
                         var viewArgs = JsonSerializer.Deserialize<Dictionary<string, string>>(argsJson);
                        if (viewArgs != null && viewArgs.TryGetValue("viewName", out var vName))
                            resultText = SqlDefinitionTools.GetViewDefinition(connectionString, vName);
                        else 
                            throw new ArgumentException("viewName is required");
                        break;
                    case "sql_db_execute_query":
                        var qArgs = JsonSerializer.Deserialize<Dictionary<string, string>>(argsJson);
                        if (qArgs != null && qArgs.TryGetValue("query", out var query))
                            resultText = SqlQueryTools.ExecuteQuery(connectionString, query);
                        else 
                            throw new ArgumentException("query is required");
                        break;
                    default:
                        throw new MethodAccessException($"Unknown tool: {toolName}");
                }

                SendResponse(message.Id, new 
                {
                    content = new[] 
                    {
                        new { type = "text", text = resultText }
                    }
                });

            }
            catch (Exception ex)
            {
                SendError(message.Id, -32603, ex.Message);
            }
        }
        else 
        {
            // Ignore other messages or send method not found if it requires response
             if (message.Id != null)
                {
                   // SendError(message.Id, -32601, "Method not found");
                }
        }
    }
    catch (Exception ex)
    {
        // Log error to stderr
        Console.Error.WriteLine($"Error processing message: {ex.Message}");
    }
}


void SendResponse(object? id, object result)
{
    if (id == null) return;
    var response = new 
    {
        jsonrpc = "2.0",
        id,
        result
    };
    Console.WriteLine(JsonSerializer.Serialize(response));
}

void SendError(object? id, int code, string message)
{
    if (id == null) return;
    var response = new 
    {
        jsonrpc = "2.0",
        id,
        error = new { code, message }
    };
    Console.WriteLine(JsonSerializer.Serialize(response));
}

class JsonRpcMessage
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "";
    [JsonPropertyName("method")]
    public string? Method { get; set; }
    [JsonPropertyName("params")]
    public object? Params { get; set; }
    [JsonPropertyName("id")]
    public object? Id { get; set; }
}

class ToolCallParams
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }
    [JsonPropertyName("arguments")]
    public object? Arguments { get; set; }
}
