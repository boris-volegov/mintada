using System.Text.Json;
using Npgsql;
using System.Text.RegularExpressions;

namespace Mintada.Mcp.Postgres;

public static class SqlDiscoveryTools
{
    public static string ListTables(string connectionString)
    {
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = """
            SELECT table_schema || '.' || table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name;
            """;

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
        (var schemaName, var objectName) = ParseObjectName(tableName);

        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = """
            SELECT
                ordinal_position,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = @schemaName
              AND table_name = @tableName
            ORDER BY ordinal_position;
            """;
        command.Parameters.AddWithValue("@schemaName", schemaName);
        command.Parameters.AddWithValue("@tableName", objectName);

        var columns = new List<object>();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            columns.Add(new
            {
                ordinal_position = reader.GetInt32(0),
                name = reader.GetString(1),
                type = reader.GetString(2),
                is_nullable = string.Equals(reader.GetString(3), "YES", StringComparison.OrdinalIgnoreCase),
                default_value = reader.IsDBNull(4) ? null : reader.GetValue(4)
            });
        }

        return JsonSerializer.Serialize(columns, new JsonSerializerOptions { WriteIndented = true });
    }

    public static string GetDatabaseInfo(string connectionString)
    {
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = "SELECT version();";
        var version = command.ExecuteScalar()?.ToString();

        command.CommandText = "SELECT current_database();";
        var databaseName = command.ExecuteScalar()?.ToString();

        return JsonSerializer.Serialize(new
        {
            Database = "PostgreSQL",
            Name = databaseName,
            Version = version
        });
    }

    private static (string schemaName, string objectName) ParseObjectName(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            throw new ArgumentException("Object name is required.");
        }

        var parts = input.Split('.', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (parts.Length is < 1 or > 2)
        {
            throw new ArgumentException("Object name must be table or schema.table.");
        }

        var schemaName = parts.Length == 2 ? parts[0] : "public";
        var objectName = parts.Length == 2 ? parts[1] : parts[0];

        if (!IsSafeIdentifier(schemaName) || !IsSafeIdentifier(objectName))
        {
            throw new ArgumentException("Invalid object name.");
        }

        return (schemaName, objectName);
    }

    private static bool IsSafeIdentifier(string value)
    {
        return Regex.IsMatch(value, "^[a-zA-Z_][a-zA-Z0-9_]*$");
    }
}
