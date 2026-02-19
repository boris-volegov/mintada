using Npgsql;
using System.Text.RegularExpressions;

namespace Mintada.Mcp.Postgres;

public static class SqlDefinitionTools
{
    public static string GetStoredProcedureDefinition(string connectionString, string procedureName)
    {
        (var schemaName, var objectName) = ParseObjectName(procedureName);

        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = """
            SELECT pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = @schemaName
              AND p.proname = @objectName
            ORDER BY p.oid
            LIMIT 1;
            """;
        command.Parameters.AddWithValue("@schemaName", schemaName);
        command.Parameters.AddWithValue("@objectName", objectName);

        var result = command.ExecuteScalar();
        return result?.ToString() ?? "Stored procedure/function not found.";
    }

    public static string GetViewDefinition(string connectionString, string viewName)
    {
        (var schemaName, var objectName) = ParseObjectName(viewName);

        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = """
            SELECT definition
            FROM pg_views
            WHERE schemaname = @schemaName
              AND viewname = @viewName;
            """;
        command.Parameters.AddWithValue("@schemaName", schemaName);
        command.Parameters.AddWithValue("@viewName", objectName);

        var result = command.ExecuteScalar();
        return result?.ToString() ?? "View not found.";
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
            throw new ArgumentException("Object name must be object or schema.object.");
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
