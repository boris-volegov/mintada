using System.Data;
using Microsoft.Data.Sqlite;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Mintada.Mcp;

public static class SqlDiscoveryTools
{
    public static string ListTables(string connectionString)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;";
        
        var tables = new List<string>();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            tables.Add(reader.GetString(0));
        }

        return string.Join(", ", tables);
    }

    public static string GetTableSchema(string connectionString, string tableName)
    {
         using var connection = new SqliteConnection(connectionString);
        connection.Open();

        // Validate table name to prevent injection via PRAGMA (though param binding doesn't work for PRAGMA)
        // Simple check to ensure it's a valid identifier
        if (!System.Text.RegularExpressions.Regex.IsMatch(tableName, "^[a-zA-Z0-9_]+$"))
        {
            throw new ArgumentException("Invalid table name.");
        }

        var command = connection.CreateCommand();
        command.CommandText = $"PRAGMA table_info({tableName});";
        
        var columns = new List<object>();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            columns.Add(new 
            {
                cid = reader.GetInt32(0),
                name = reader.GetString(1),
                type = reader.GetString(2),
                notnull = reader.GetInt32(3),
                dflt_value = reader.IsDBNull(4) ? null : reader.GetValue(4),
                pk = reader.GetInt32(5)
            });
        }

        return JsonSerializer.Serialize(columns, new JsonSerializerOptions { WriteIndented = true });
    }

    public static string GetDatabaseInfo(string connectionString)
    {
        using var connection = new SqliteConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = "SELECT sqlite_version();";
        var version = command.ExecuteScalar()?.ToString();

        // Get file size if possible vs DB stats
        // Just return version for now plus stats
        return JsonSerializer.Serialize(new { 
            Database = "SQLite",
            Version = version
        });
    }
}
