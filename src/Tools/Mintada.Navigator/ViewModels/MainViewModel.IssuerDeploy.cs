using CommunityToolkit.Mvvm.Input;
using Mintada.Navigator.Models;
using Mintada.Navigator.Services;

namespace Mintada.Navigator.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private async Task DeployIssuer(object? parameter)
    {
        var issuer = ResolveIssuer(parameter);
        if (issuer == null)
        {
            StatusMessage = "Deploy failed: issuer is not selected.";
            return;
        }

        try
        {
            var deployRows = BuildDeployRows(issuer);
            if (deployRows.Count == 0)
            {
                StatusMessage = "Deploy skipped: no issuer rows available.";
                return;
            }

            StatusMessage = $"Deploying issuer {issuer.Name} ({issuer.UrlSlug}) to Postgres...";

            var deployService = new PostgresIssuerDeployService(GetPostgresConnectionString());
            await deployService.UpsertIssuersAsync(deployRows);

            var parentCount = Math.Max(0, deployRows.Count - 1);
            StatusMessage = $"Deploy completed: {issuer.Name} (with {parentCount} parent row(s)).";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Deploy failed: {ex.Message}";
        }
    }

    private Issuer? ResolveIssuer(object? parameter)
    {
        if (parameter is Issuer issuer)
        {
            return _allIssuers.FirstOrDefault(i => i.Id == issuer.Id) ?? issuer;
        }

        if (parameter is LeafIssuerViewModel leafIssuer)
        {
            return _allIssuers.FirstOrDefault(i => i.Id == leafIssuer.Id);
        }

        if (parameter is long issuerId)
        {
            return _allIssuers.FirstOrDefault(i => i.Id == issuerId);
        }

        return SelectedIssuer;
    }

    private List<PostgresIssuerRow> BuildDeployRows(Issuer issuer)
    {
        var slugLookup = BuildSlugLookup();
        var deploymentChain = GetIssuerDeploymentChain(issuer, slugLookup);
        var rows = new List<PostgresIssuerRow>(deploymentChain.Count);

        foreach (var chainIssuer in deploymentChain)
        {
            var parentId = ResolveParentId(chainIssuer, slugLookup);
            rows.Add(new PostgresIssuerRow(
                Id: ToPostgresIntId(chainIssuer.Id),
                ParentId: parentId,
                Name: chainIssuer.Name,
                UrlSlug: chainIssuer.UrlSlug,
                TerritoryType: chainIssuer.TerritoryType,
                IsHistoricalPeriod: chainIssuer.IsHistoricalPeriod,
                IsSection: chainIssuer.IsSection
            ));
        }

        return rows;
    }

    private Dictionary<string, Issuer> BuildSlugLookup()
    {
        return _allIssuers
            .Where(i => !string.IsNullOrWhiteSpace(i.UrlSlug))
            .GroupBy(i => i.UrlSlug!, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.First(), StringComparer.OrdinalIgnoreCase);
    }

    private static List<Issuer> GetIssuerDeploymentChain(Issuer issuer, IReadOnlyDictionary<string, Issuer> slugLookup)
    {
        var stack = new Stack<Issuer>();
        var visited = new HashSet<long>();
        var current = issuer;

        while (current != null && visited.Add(current.Id))
        {
            stack.Push(current);

            if (string.IsNullOrWhiteSpace(current.ParentUrlSlug) || !slugLookup.TryGetValue(current.ParentUrlSlug, out var parent))
            {
                break;
            }

            current = parent;
        }

        return stack.ToList();
    }

    private static int? ResolveParentId(Issuer issuer, IReadOnlyDictionary<string, Issuer> slugLookup)
    {
        if (string.IsNullOrWhiteSpace(issuer.ParentUrlSlug))
        {
            return null;
        }

        if (!slugLookup.TryGetValue(issuer.ParentUrlSlug, out var parent))
        {
            return null;
        }

        return ToPostgresIntId(parent.Id);
    }

    private static int ToPostgresIntId(long id)
    {
        return checked((int)id);
    }

    private static string GetPostgresConnectionString()
    {
        var fromMintada = Environment.GetEnvironmentVariable("MINTADA_PG_CONNECTION_STRING");
        if (!string.IsNullOrWhiteSpace(fromMintada))
        {
            return fromMintada;
        }

        var fromPg = Environment.GetEnvironmentVariable("PG_CONNECTION_STRING");
        if (!string.IsNullOrWhiteSpace(fromPg))
        {
            return fromPg;
        }

        return "Host=localhost;Port=5432;Database=mintada_db;Username=admin;Password=mintada";
    }
}
