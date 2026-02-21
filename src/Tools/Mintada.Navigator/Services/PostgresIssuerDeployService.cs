using Npgsql;

namespace Mintada.Navigator.Services;

public class PostgresIssuerDeployService
{
    private readonly string _connectionString;

    public PostgresIssuerDeployService(string connectionString)
    {
        _connectionString = connectionString;
    }

    public async Task UpsertIssuersAsync(IEnumerable<PostgresIssuerRow> issuers, CancellationToken cancellationToken = default)
    {
        var rows = issuers.ToList();
        if (rows.Count == 0)
        {
            return;
        }

        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var transaction = await connection.BeginTransactionAsync(cancellationToken);

        const string sql = """
            INSERT INTO issuers ("Id", "ParentId", "IssuerTypeId", "Name", "UrlSlug", "TerritoryType", "IsHistoricalPeriod", "IsSection", "IsRulersContainer")
            VALUES (@id, @parentId, NULL, @name, @urlSlug, @territoryType, @isHistoricalPeriod, @isSection, FALSE)
            ON CONFLICT ("Id")
            DO UPDATE
            SET "ParentId" = EXCLUDED."ParentId",
                "Name" = EXCLUDED."Name",
                "UrlSlug" = EXCLUDED."UrlSlug",
                "TerritoryType" = EXCLUDED."TerritoryType",
                "IsHistoricalPeriod" = EXCLUDED."IsHistoricalPeriod",
                "IsSection" = EXCLUDED."IsSection";
            """;

        foreach (var issuer in rows)
        {
            await using var command = new NpgsqlCommand(sql, connection, transaction);
            command.Parameters.AddWithValue("id", issuer.Id);
            command.Parameters.AddWithValue("parentId", issuer.ParentId.HasValue ? issuer.ParentId.Value : DBNull.Value);
            command.Parameters.AddWithValue("name", string.IsNullOrWhiteSpace(issuer.Name) ? DBNull.Value : issuer.Name);
            command.Parameters.AddWithValue("urlSlug", string.IsNullOrWhiteSpace(issuer.UrlSlug) ? DBNull.Value : issuer.UrlSlug);
            command.Parameters.AddWithValue("territoryType", string.IsNullOrWhiteSpace(issuer.TerritoryType) ? DBNull.Value : issuer.TerritoryType);
            command.Parameters.AddWithValue("isHistoricalPeriod", issuer.IsHistoricalPeriod);
            command.Parameters.AddWithValue("isSection", issuer.IsSection);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }

        await transaction.CommitAsync(cancellationToken);
    }
}

public sealed record PostgresIssuerRow(
    int Id,
    int? ParentId,
    string? Name,
    string? UrlSlug,
    string? TerritoryType,
    bool IsHistoricalPeriod,
    bool IsSection
);
