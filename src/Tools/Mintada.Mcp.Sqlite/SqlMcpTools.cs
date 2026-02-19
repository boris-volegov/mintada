using ModelContextProtocol.Server;

namespace Mintada.Mcp.Sqlite;

[McpServerToolType]
public sealed class SqlMcpTools
{
    private readonly string _connectionString;

    public SqlMcpTools()
    {
        string dbPath = Environment.GetEnvironmentVariable("DB_PATH") ?? "/data/numista/coins.db";
        _connectionString = $"Data Source={dbPath}";
    }

    [McpServerTool(Name = "sql_db_list_tables")]
    public string ListTables() => SqlDiscoveryTools.ListTables(_connectionString);

    [McpServerTool(Name = "sql_db_get_table_schema")]
    public string GetTableSchema(string tableName) => SqlDiscoveryTools.GetTableSchema(_connectionString, tableName);

    [McpServerTool(Name = "sql_db_get_database_info")]
    public string GetDatabaseInfo() => SqlDiscoveryTools.GetDatabaseInfo(_connectionString);

    [McpServerTool(Name = "sql_db_get_stored_procedure_definition")]
    public string GetStoredProcedureDefinition(string procedureName) => SqlDefinitionTools.GetStoredProcedureDefinition(_connectionString, procedureName);

    [McpServerTool(Name = "sql_db_get_view_definition")]
    public string GetViewDefinition(string viewName) => SqlDefinitionTools.GetViewDefinition(_connectionString, viewName);

    [McpServerTool(Name = "sql_db_execute_query")]
    public string ExecuteQuery(string query) => SqlQueryTools.ExecuteQuery(_connectionString, query);
}

