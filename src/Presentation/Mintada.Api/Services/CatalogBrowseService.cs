using System.Data;
using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using Mintada.Api.Dtos;
using Mintada.Data;

namespace Mintada.Api.Services;

public class CatalogBrowseService : ICatalogBrowseService
{
    private readonly MintadaDbContext _context;

    public CatalogBrowseService(MintadaDbContext context)
    {
        _context = context;
    }

    public async Task<IEnumerable<CatalogIssuerRulerNodeDto>> GetRulerBrowserAsync(CancellationToken cancellationToken = default)
    {
        var issuers = await _context.Issuers
            .Select(i => new CatalogIssuerRulerNodeDto
            {
                Id = i.Id,
                ParentId = i.ParentId,
                Name = i.Name,
                UrlSlug = i.UrlSlug,
                TerritoryType = i.TerritoryType,
                IsHistoricalPeriod = i.IsHistoricalPeriod,
                IsSection = i.IsSection
            })
            .ToListAsync(cancellationToken);

        var nodesById = issuers.ToDictionary(i => i.Id);
        var roots = new List<CatalogIssuerRulerNodeDto>();

        foreach (var issuer in issuers)
        {
            if (issuer.ParentId.HasValue && nodesById.TryGetValue(issuer.ParentId.Value, out var parent))
            {
                parent.Children.Add(issuer);
            }
            else
            {
                roots.Add(issuer);
            }
        }

        var leafIssuerIds = nodesById.Values
            .Where(i => i.Children.Count == 0)
            .Select(i => i.Id)
            .ToHashSet();

        var relationRows = await LoadIssuerRulerRowsAsync(cancellationToken);
        var seenByIssuer = new Dictionary<int, HashSet<string>>();

        foreach (var row in relationRows)
        {
            if (!leafIssuerIds.Contains(row.IssuerId))
            {
                continue;
            }

            if (!nodesById.TryGetValue(row.IssuerId, out var issuerNode))
            {
                continue;
            }

            if (!seenByIssuer.TryGetValue(row.IssuerId, out var seen))
            {
                seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                seenByIssuer[row.IssuerId] = seen;
            }

            var dedupKey = $"{row.RulerId}|{(row.RuleType ?? string.Empty).Trim()}";
            if (!seen.Add(dedupKey))
            {
                continue;
            }

            var displayName = !string.IsNullOrWhiteSpace(row.IssuerRulerName)
                ? row.IssuerRulerName!
                : (!string.IsNullOrWhiteSpace(row.RulerName) ? row.RulerName! : $"Ruler {row.RulerId}");

            issuerNode.Rulers.Add(new CatalogRulerDto
            {
                Id = row.RulerId,
                Name = displayName,
                RuleType = row.RuleType,
                Title = row.RulerTitle
            });
        }

        foreach (var node in nodesById.Values)
        {
            if (node.Rulers.Count > 1)
            {
                node.Rulers = node.Rulers
                    .OrderBy(r => r.Name, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }
        }

        PruneRootsWithoutRulers(roots);
        SortTree(roots);
        ComputeStats(roots);

        return roots;
    }

    private async Task<List<IssuerRulerRow>> LoadIssuerRulerRowsAsync(CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT
                ir.issuer_id,
                ir.ruler_id,
                ir.name AS issuer_ruler_name,
                ir.rule_type,
                r.name AS ruler_name,
                r.title AS ruler_title
            FROM issuers_rulers_rel ir
            LEFT JOIN rulers r ON r.id = ir.ruler_id
            WHERE ir.issuer_id IS NOT NULL
              AND ir.ruler_id IS NOT NULL;
            """;

        var rows = new List<IssuerRulerRow>();
        await using var command = _context.Database.GetDbConnection().CreateCommand();
        command.CommandText = sql;

        if (command.Connection?.State != ConnectionState.Open)
        {
            await command.Connection!.OpenAsync(cancellationToken);
        }

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);

        var issuerIdOrdinal = reader.GetOrdinal("issuer_id");
        var rulerIdOrdinal = reader.GetOrdinal("ruler_id");
        var issuerRulerNameOrdinal = reader.GetOrdinal("issuer_ruler_name");
        var ruleTypeOrdinal = reader.GetOrdinal("rule_type");
        var rulerNameOrdinal = reader.GetOrdinal("ruler_name");
        var rulerTitleOrdinal = reader.GetOrdinal("ruler_title");

        while (await reader.ReadAsync(cancellationToken))
        {
            var issuerId = ReadInt(reader, issuerIdOrdinal);
            var rulerId = ReadInt(reader, rulerIdOrdinal);

            rows.Add(new IssuerRulerRow
            {
                IssuerId = issuerId,
                RulerId = rulerId,
                IssuerRulerName = ReadString(reader, issuerRulerNameOrdinal),
                RuleType = ReadString(reader, ruleTypeOrdinal),
                RulerName = ReadString(reader, rulerNameOrdinal),
                RulerTitle = ReadString(reader, rulerTitleOrdinal)
            });
        }

        return rows;
    }

    private static int ReadInt(DbDataReader reader, int ordinal)
    {
        var value = reader.GetValue(ordinal);

        return value switch
        {
            int v => v,
            long v => Convert.ToInt32(v),
            short v => v,
            byte v => v,
            decimal v => Convert.ToInt32(v),
            string s when int.TryParse(s, out var parsed) => parsed,
            _ => Convert.ToInt32(value)
        };
    }

    private static string? ReadString(DbDataReader reader, int ordinal)
    {
        if (reader.IsDBNull(ordinal))
        {
            return null;
        }

        return Convert.ToString(reader.GetValue(ordinal));
    }

    private static void PruneRootsWithoutRulers(List<CatalogIssuerRulerNodeDto> roots)
    {
        roots.RemoveAll(root => !PruneNode(root));
    }

    private static bool PruneNode(CatalogIssuerRulerNodeDto node)
    {
        node.Children.RemoveAll(child => !PruneNode(child));
        return node.Rulers.Count > 0 || node.Children.Count > 0;
    }

    private static void SortTree(List<CatalogIssuerRulerNodeDto> nodes)
    {
        nodes.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));

        foreach (var node in nodes)
        {
            if (node.Children.Count > 0)
            {
                SortTree(node.Children);
            }
        }
    }

    private static void ComputeStats(List<CatalogIssuerRulerNodeDto> roots)
    {
        foreach (var root in roots)
        {
            ComputeStats(root);
        }
    }

    private static (int leafIssuerCountWithRulers, int rulerCountInSubtree) ComputeStats(CatalogIssuerRulerNodeDto node)
    {
        if (node.Children.Count == 0)
        {
            var leafIssuerCountWithRulers = node.Rulers.Count > 0 ? 1 : 0;
            var rulerCount = node.Rulers.Count;
            node.LeafIssuerCountWithRulers = leafIssuerCountWithRulers;
            node.RulerCountInSubtree = rulerCount;
            return (leafIssuerCountWithRulers, rulerCount);
        }

        var leafCount = 0;
        var rulerCountInSubtree = 0;

        foreach (var child in node.Children)
        {
            var (childLeafCount, childRulerCount) = ComputeStats(child);
            leafCount += childLeafCount;
            rulerCountInSubtree += childRulerCount;
        }

        node.LeafIssuerCountWithRulers = leafCount;
        node.RulerCountInSubtree = rulerCountInSubtree;
        return (leafCount, rulerCountInSubtree);
    }

    private sealed class IssuerRulerRow
    {
        public int IssuerId { get; init; }
        public int RulerId { get; init; }
        public string? IssuerRulerName { get; init; }
        public string? RuleType { get; init; }
        public string? RulerName { get; init; }
        public string? RulerTitle { get; init; }
    }
}
