using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Mintada.Api.Dtos;
using Mintada.Data;

namespace Mintada.Api.Controllers;

[ApiController]
[Route("api/rulers")]
public class RulersController : ControllerBase
{
    private readonly MintadaDbContext _context;

    public RulersController(MintadaDbContext context)
    {
        _context = context;
    }

    [HttpGet("{id:int}/coin-types")]
    public async Task<ActionResult<RulerCoinTypesResponseDto>> GetCoinTypesByRulerId(
        int id,
        CancellationToken cancellationToken)
    {
        var ruler = await _context.Rulers
            .Where(r => r.Id == id)
            .Select(r => new { r.Id, r.Name, r.PortraitUrl, r.Info })
            .FirstOrDefaultAsync(cancellationToken);

        if (ruler is null)
        {
            return NotFound();
        }

        var rows = await _context.CoinTypesIssuersRulersRel
            .Where(link => link.IssuerRulerRel.RulerId == id)
            .Select(link => new
            {
                IssuerId = link.CoinType.IssuerId,
                IssuerName = link.CoinType.Issuer.Name,
                IssuerUrlSlug = link.CoinType.Issuer.UrlSlug,
                TerritoryType = link.CoinType.Issuer.TerritoryType,
                CoinTypeId = link.CoinType.Id,
                link.CoinType.Title,
                link.CoinType.Subtitle,
                Period = link.CoinType.CoinagePeriod != null ? link.CoinType.CoinagePeriod.Name : null,
                link.CoinType.RarityIndex,
                CoinTypeSlug = link.CoinType.UrlSlug,
                link.CoinType.DateTimeInserted,
                link.CoinType.IssueTypeId,
                ObverseImage = link.CoinType.Samples
                    .Where(s => s.SampleType == 1)
                    .Select(s => s.ObverseImage)
                    .FirstOrDefault(),
                ReverseImage = link.CoinType.Samples
                    .Where(s => s.SampleType == 1)
                    .Select(s => s.ReverseImage)
                    .FirstOrDefault()
            })
            .ToListAsync(cancellationToken);

        var issuerGroups = rows
            .GroupBy(row => new
            {
                row.IssuerId,
                row.IssuerName,
                row.IssuerUrlSlug,
                row.TerritoryType
            })
            .Select(group => new RulerIssuerCoinTypeGroupDto
            {
                IssuerId = group.Key.IssuerId,
                IssuerName = group.Key.IssuerName,
                IssuerUrlSlug = group.Key.IssuerUrlSlug,
                TerritoryType = group.Key.TerritoryType,
                CoinTypes = group
                    .GroupBy(item => item.CoinTypeId)
                    .Select(coinGroup => coinGroup.First())
                    .OrderBy(item => item.Title)
                    .ThenBy(item => item.CoinTypeId)
                    .Select(item => new RulerCoinTypeItemDto
                    {
                        Id = item.CoinTypeId,
                        Title = item.Title,
                        Subtitle = item.Subtitle,
                        Period = item.Period,
                        RarityIndex = item.RarityIndex,
                        CoinTypeSlug = item.CoinTypeSlug,
                        DateTimeInserted = item.DateTimeInserted,
                        IssueTypeId = item.IssueTypeId,
                        ObverseImage = item.ObverseImage,
                        ReverseImage = item.ReverseImage
                    })
                    .ToList()
            })
            .OrderBy(group => group.IssuerName)
            .ThenBy(group => group.IssuerId)
            .ToList();

        var response = new RulerCoinTypesResponseDto
        {
            RulerId = ruler.Id,
            RulerName = ruler.Name,
            PortraitUrl = ruler.PortraitUrl,
            InfoHtml = ruler.Info,
            HasMultipleIssuers = issuerGroups.Count > 1,
            IssuerGroups = issuerGroups
        };

        return Ok(response);
    }
}
