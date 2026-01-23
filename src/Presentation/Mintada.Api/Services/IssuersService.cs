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
        // 1. Fetch all issuers
        var issuers = await _context.Issuers
            .Select(i => new IssuerTreeDto
            {
                Id = i.Id,
                ParentId = i.ParentId,
                Url = i.Url,
                Name = i.Name,
                UrlSlug = i.UrlSlug,
                TerritoryType = i.TerritoryType,
                IsHistoricalPeriod = i.IsHistoricalPeriod,
                IsSection = i.IsSection
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

        // 3. Optional: Sort roots and children by Name for consistent display
        // Recursive sorting might be needed if we want alphabetical order everywhere.
        SortTree(roots);

        return roots;
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
