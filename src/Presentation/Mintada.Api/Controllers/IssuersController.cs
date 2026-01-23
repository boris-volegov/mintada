using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Mintada.Api.Dtos;
using Mintada.Data;
using Mintada.Domain.Entities;

namespace Mintada.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class IssuersController : ControllerBase
{
    private readonly MintadaDbContext _context;
    private readonly Mintada.Api.Services.IIssuersService _issuersService;

    public IssuersController(MintadaDbContext context, Mintada.Api.Services.IIssuersService issuersService)
    {
        _context = context;
        _issuersService = issuersService;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<IssuerDto>>> GetIssuers()
    {
        return await _context.Issuers
            .Select(i => new IssuerDto
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
    }

    [HttpGet("hierarchy")]
    public async Task<ActionResult<IEnumerable<IssuerTreeDto>>> GetIssuerHierarchy()
    {
        var result = await _issuersService.GetIssuerHierarchyAsync();
        return Ok(result);
    }
    
    // Explicit route for integer IDs
    [HttpGet("{id:int}/coin-types")]
    public async Task<ActionResult<IEnumerable<CoinTypeDto>>> GetCoinTypesByIssuerId(int id)
    {
        var coinTypes = await _context.CoinTypes
            .Where(ct => ct.IssuerId == id)
            .Select(ct => new CoinTypeDto
            {
                Id = ct.Id,
                IssuerId = ct.IssuerId,
                Title = ct.Title,
                Subtitle = ct.Subtitle,
                EdgeImage = ct.EdgeImage,
                Period = ct.Period,
                RarityIndex = ct.RarityIndex,
                CoinTypeSlug = ct.CoinTypeSlug,
                DateTimeInserted = ct.DateTimeInserted,
                IssueTypeId = ct.IssueTypeId,
                ObverseImage = ct.Samples.Where(s => s.SampleType == 1).Select(s => s.ObverseImage).FirstOrDefault(),
                ReverseImage = ct.Samples.Where(s => s.SampleType == 1).Select(s => s.ReverseImage).FirstOrDefault()
            })
            .ToListAsync();
            
        return Ok(coinTypes);
    }

    // Explicit route for string slugs (fallback)
    [HttpGet("{slug}/coin-types")]
    public async Task<ActionResult<IEnumerable<CoinTypeDto>>> GetCoinTypesByIssuerSlug(string slug)
    {
         var coinTypes = await _context.CoinTypes
            .Where(ct => ct.Issuer.UrlSlug == slug)
            .Select(ct => new CoinTypeDto
            {
                Id = ct.Id,
                IssuerId = ct.IssuerId,
                Title = ct.Title,
                Subtitle = ct.Subtitle,
                EdgeImage = ct.EdgeImage,
                Period = ct.Period,
                RarityIndex = ct.RarityIndex,
                CoinTypeSlug = ct.CoinTypeSlug,
                DateTimeInserted = ct.DateTimeInserted,
                IssueTypeId = ct.IssueTypeId,
                ObverseImage = ct.Samples.Where(s => s.SampleType == 1).Select(s => s.ObverseImage).FirstOrDefault(),
                ReverseImage = ct.Samples.Where(s => s.SampleType == 1).Select(s => s.ReverseImage).FirstOrDefault()
            })
            .ToListAsync();
            
        return Ok(coinTypes);
    }
}
