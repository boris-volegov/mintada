using Npgsql;
using System.Text.Json;

namespace Mintada.Mcp.Postgres;

public static class SqlQueryTools
{
    public static string ExecuteQuery(string connectionString, string query)
    {
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText = query;
        
        var results = new List<Dictionary<string, object?>>();

        try 
        {
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var row = new Dictionary<string, object?>();
                for (int i = 0; i < reader.FieldCount; i++)
                {
                    var name = reader.GetName(i);
                    var value = reader.IsDBNull(i) ? null : NormalizeValue(reader.GetValue(i));
                    row[name] = value;
                }
                results.Add(row);
            }
            return JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            return $"Error executing query: {ex.Message}";
        }
    }

    private static object? NormalizeValue(object value)
    {
        return value switch
        {
            byte[] bytes => Convert.ToBase64String(bytes),
            DateOnly dateOnly => dateOnly.ToString("yyyy-MM-dd"),
            TimeOnly timeOnly => timeOnly.ToString("HH:mm:ss.fffffff"),
            TimeSpan timeSpan => timeSpan.ToString(),
            _ => value
        };
    }
}
