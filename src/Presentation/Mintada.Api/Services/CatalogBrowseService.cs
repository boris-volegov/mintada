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
                IsSection = i.IsSection,
                IsRulersContainer = i.IsRulersContainer
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

        var relationRows = await LoadIssuerRulerRowsAsync(cancellationToken);
        var relationRowsByIssuer = relationRows
            .GroupBy(row => row.IssuerId)
            .ToDictionary(group => group.Key, group => group.ToList());

        var containerLeafIssuerCountOverrides = FlattenRulerContainerSections(roots, relationRowsByIssuer);

        var leafIssuerIds = CollectLeafIssuerIds(roots);
        AttachLeafIssuerRulers(leafIssuerIds, nodesById, relationRowsByIssuer);

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
        ComputeStats(roots, containerLeafIssuerCountOverrides);

        return roots;
    }

    private async Task<List<IssuerRulerRow>> LoadIssuerRulerRowsAsync(CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT
                ir."IssuerId" AS issuer_id,
                ir."RulerId" AS ruler_id,
                ir."Name" AS issuer_ruler_name,
                ir."RuleType" AS rule_type,
                ir."GroupId" AS group_id,
                g."Name" AS group_name,
                r."Name" AS ruler_name,
                NULL::text AS ruler_title
            FROM issuers_rulers_rel ir
            LEFT JOIN issuers_rulers_rel_groups g
                ON g."Id" = ir."GroupId"
                AND g."IssuerId" = ir."IssuerId"
            LEFT JOIN rulers r ON r."Id" = ir."RulerId"
            WHERE ir."IssuerId" IS NOT NULL
              AND ir."RulerId" IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM coin_types_issuers_rulers_rel ctirr
                  WHERE ctirr."IssuerRulerRelId" = ir."Id"
              );
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
        var groupIdOrdinal = reader.GetOrdinal("group_id");
        var groupNameOrdinal = reader.GetOrdinal("group_name");
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
                GroupId = ReadNullableInt(reader, groupIdOrdinal),
                GroupName = ReadString(reader, groupNameOrdinal),
                RulerName = ReadString(reader, rulerNameOrdinal),
                RulerTitle = ReadString(reader, rulerTitleOrdinal)
            });
        }

        return rows;
    }

    private static Dictionary<int, int> FlattenRulerContainerSections(
        List<CatalogIssuerRulerNodeDto> roots,
        IReadOnlyDictionary<int, List<IssuerRulerRow>> relationRowsByIssuer)
    {
        var containerLeafIssuerCountOverrides = new Dictionary<int, int>();
        var allNodes = new List<CatalogIssuerRulerNodeDto>();

        foreach (var root in roots)
        {
            CollectNodesPreOrder(root, allNodes);
        }

        foreach (var node in allNodes)
        {
            if (!node.IsSection || !node.IsRulersContainer)
            {
                continue;
            }

            var descendantIssuerIds = new HashSet<int>();
            CollectDescendantIssuerIds(node, descendantIssuerIds);

            var issuersWithRulers = new HashSet<int>();
            var distinctRulers = new Dictionary<(int rulerId, string name), CatalogRulerDto>();

            foreach (var issuerId in descendantIssuerIds)
            {
                if (!relationRowsByIssuer.TryGetValue(issuerId, out var issuerRows) || issuerRows.Count == 0)
                {
                    continue;
                }

                issuersWithRulers.Add(issuerId);

                foreach (var row in issuerRows)
                {
                    var displayName = GetDisplayName(row);
                    var dedupKey = (row.RulerId, displayName);

                    if (distinctRulers.TryGetValue(dedupKey, out var existingRuler))
                    {
                        if (existingRuler.GroupId is null && row.GroupId is not null)
                        {
                            existingRuler.GroupId = row.GroupId;
                            existingRuler.GroupName = row.GroupName;
                        }

                        continue;
                    }

                    distinctRulers[dedupKey] = new CatalogRulerDto
                    {
                        Id = row.RulerId,
                        Name = displayName,
                        RuleType = row.RuleType,
                        Title = row.RulerTitle,
                        GroupId = row.GroupId,
                        GroupName = row.GroupName
                    };
                }
            }

            node.Rulers = distinctRulers.Values
                .OrderBy(r => r.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();

            node.Children.Clear();
            containerLeafIssuerCountOverrides[node.Id] = issuersWithRulers.Count;
        }

        return containerLeafIssuerCountOverrides;
    }

    private static void CollectNodesPreOrder(CatalogIssuerRulerNodeDto node, List<CatalogIssuerRulerNodeDto> nodes)
    {
        nodes.Add(node);

        foreach (var child in node.Children)
        {
            CollectNodesPreOrder(child, nodes);
        }
    }

    private static void CollectDescendantIssuerIds(CatalogIssuerRulerNodeDto node, HashSet<int> issuerIds)
    {
        foreach (var child in node.Children)
        {
            issuerIds.Add(child.Id);
            CollectDescendantIssuerIds(child, issuerIds);
        }
    }

    private static HashSet<int> CollectLeafIssuerIds(List<CatalogIssuerRulerNodeDto> roots)
    {
        var leafIssuerIds = new HashSet<int>();

        foreach (var root in roots)
        {
            CollectLeafIssuerIds(root, leafIssuerIds);
        }

        return leafIssuerIds;
    }

    private static void CollectLeafIssuerIds(CatalogIssuerRulerNodeDto node, HashSet<int> leafIssuerIds)
    {
        if (node.Children.Count == 0)
        {
            leafIssuerIds.Add(node.Id);
            return;
        }

        foreach (var child in node.Children)
        {
            CollectLeafIssuerIds(child, leafIssuerIds);
        }
    }

    private static void AttachLeafIssuerRulers(
        HashSet<int> leafIssuerIds,
        IReadOnlyDictionary<int, CatalogIssuerRulerNodeDto> nodesById,
        IReadOnlyDictionary<int, List<IssuerRulerRow>> relationRowsByIssuer)
    {
        foreach (var issuerId in leafIssuerIds)
        {
            if (!nodesById.TryGetValue(issuerId, out var issuerNode))
            {
                continue;
            }

            if (issuerNode.IsSection && issuerNode.IsRulersContainer)
            {
                continue;
            }

            if (!relationRowsByIssuer.TryGetValue(issuerId, out var issuerRows) || issuerRows.Count == 0)
            {
                continue;
            }

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (var row in issuerRows)
            {
                var dedupKey = $"{row.RulerId}|{GetDisplayName(row)}|{(row.RuleType ?? string.Empty).Trim()}|{row.GroupId?.ToString() ?? string.Empty}|{(row.GroupName ?? string.Empty).Trim()}";
                if (!seen.Add(dedupKey))
                {
                    continue;
                }

                issuerNode.Rulers.Add(new CatalogRulerDto
                {
                    Id = row.RulerId,
                    Name = GetDisplayName(row),
                    RuleType = row.RuleType,
                    Title = row.RulerTitle,
                    GroupId = row.GroupId,
                    GroupName = row.GroupName
                });
            }
        }
    }

    private static string GetDisplayName(IssuerRulerRow row)
    {
        if (!string.IsNullOrWhiteSpace(row.IssuerRulerName))
        {
            return row.IssuerRulerName!;
        }

        if (!string.IsNullOrWhiteSpace(row.RulerName))
        {
            return row.RulerName!;
        }

        return $"Ruler {row.RulerId}";
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

    private static int? ReadNullableInt(DbDataReader reader, int ordinal)
    {
        if (reader.IsDBNull(ordinal))
        {
            return null;
        }

        return ReadInt(reader, ordinal);
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

    private static void ComputeStats(
        List<CatalogIssuerRulerNodeDto> roots,
        IReadOnlyDictionary<int, int> containerLeafIssuerCountOverrides)
    {
        foreach (var root in roots)
        {
            ComputeStats(root, containerLeafIssuerCountOverrides);
        }
    }

    private static (int leafIssuerCountWithRulers, int rulerCountInSubtree) ComputeStats(
        CatalogIssuerRulerNodeDto node,
        IReadOnlyDictionary<int, int> containerLeafIssuerCountOverrides)
    {
        if (node.IsSection && node.IsRulersContainer)
        {
            var leafIssuerCountWithRulers = containerLeafIssuerCountOverrides.GetValueOrDefault(node.Id, 0);
            var rulerCount = node.Rulers.Count;
            node.LeafIssuerCountWithRulers = leafIssuerCountWithRulers;
            node.RulerCountInSubtree = rulerCount;
            return (leafIssuerCountWithRulers, rulerCount);
        }

        if (node.Children.Count == 0)
        {
            var leafIssuerCountWithRulers = node.Rulers.Count > 0 ? 1 : 0;
            var rulerCount = node.Rulers.Count;
            node.LeafIssuerCountWithRulers = leafIssuerCountWithRulers;
            node.RulerCountInSubtree = rulerCount;
            return (leafIssuerCountWithRulers, rulerCount);
        }

        var leafCount = 0;
        var rulerCountInSubtree = node.Rulers.Count;

        foreach (var child in node.Children)
        {
            var (childLeafCount, childRulerCount) = ComputeStats(child, containerLeafIssuerCountOverrides);
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
        public int? GroupId { get; init; }
        public string? GroupName { get; init; }
        public string? RulerName { get; init; }
        public string? RulerTitle { get; init; }
    }
}
