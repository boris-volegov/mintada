using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Mintada.Api.Dtos;
using Mintada.Data;

namespace Mintada.Api.Controllers;

[ApiController]
[Route("api/coin-types")]
public class CoinTypesController : ControllerBase
{
    private readonly MintadaDbContext _context;

    public CoinTypesController(MintadaDbContext context)
    {
        _context = context;
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<CoinTypeDetailDto>> GetCoinType(int id)
    {
        var coinType = await _context.CoinTypes
            .Include(ct => ct.Samples)
            .Where(ct => ct.Id == id)
            .Select(ct => new CoinTypeDetailDto
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
                ReverseImage = ct.Samples.Where(s => s.SampleType == 1).Select(s => s.ReverseImage).FirstOrDefault(),
                Samples = ct.Samples.Select(s => new CoinTypeSampleDto 
                {
                    ObverseImage = s.ObverseImage,
                    ReverseImage = s.ReverseImage,
                    SampleType = s.SampleType
                }).ToList()
            })
            .FirstOrDefaultAsync();

        if (coinType == null)
        {
            return NotFound();
        }

        return coinType;
    }
}
