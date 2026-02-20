using Microsoft.EntityFrameworkCore;
using Mintada.Api.Dtos;
using Mintada.Data;

namespace Mintada.Api.Services;

public class IssuersService : IIssuersService
{
    private readonly MintadaDbContext _context;

    public IssuersService(MintadaDbContext context)
    {
        _context = context;
    }

    public async Task<IEnumerable<IssuerTreeDto>> GetIssuerHierarchyAsync()
    {
        var issuerIdsWithCoinTypes = await _context.CoinTypes
            .Select(ct => ct.IssuerId)
            .Distinct()
            .ToListAsync();

        if (issuerIdsWithCoinTypes.Count == 0)
        {
            return [];
        }

        var issuerIdsWithCoinTypesSet = issuerIdsWithCoinTypes.ToHashSet();

        // 1. Fetch all issuers
        var issuers = await _context.Issuers
            .Select(i => new IssuerTreeDto
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
            .ToListAsync();

        // 2. Build the tree
        var lookup = issuers.ToDictionary(i => i.Id);
        var roots = new List<IssuerTreeDto>();

        foreach (var issuer in issuers)
        {
            if (issuer.ParentId.HasValue && lookup.TryGetValue(issuer.ParentId.Value, out var parent))
            {
                parent.Children.Add(issuer);
            }
            else
            {
                // No parent, or parent not found -> treat as root
                roots.Add(issuer);
            }
        }

        // 3. Keep only branches that contain at least one issuer with coin types.
        roots.RemoveAll(root => !PruneNode(root, issuerIdsWithCoinTypesSet));

        // 4. Sort roots and children by Name for consistent display.
        SortTree(roots);

        return roots;
    }

    private static bool PruneNode(IssuerTreeDto node, HashSet<int> issuerIdsWithCoinTypes)
    {
        node.Children.RemoveAll(child => !PruneNode(child, issuerIdsWithCoinTypes));

        return issuerIdsWithCoinTypes.Contains(node.Id) || node.Children.Count > 0;
    }

    private void SortTree(List<IssuerTreeDto> nodes)
    {
        nodes.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
        
        foreach (var node in nodes)
        {
            if (node.Children.Any())
            {
                SortTree(node.Children);
            }
        }
    }
}
