using Microsoft.Data.Sqlite;

namespace Mintada.Mcp;

public static class SqlDefinitionTools
{
    public static string GetStoredProcedureDefinition(string connectionString, string procedureName)
    {
        return "SQLite does not support stored procedures.";
    }

    public static string GetViewDefinition(string connectionString, string viewName)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = "SELECT sql FROM sqlite_master WHERE type='view' AND name=@viewName;";
        command.Parameters.AddWithValue("@viewName", viewName);
        
        var result = command.ExecuteScalar();
        return result?.ToString() ?? "View not found.";
    }
}
