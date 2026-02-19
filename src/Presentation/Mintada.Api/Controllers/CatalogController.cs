using Microsoft.AspNetCore.Mvc;
using Mintada.Api.Dtos;
using Mintada.Api.Services;

namespace Mintada.Api.Controllers;

[ApiController]
[Route("api/catalog")]
public class CatalogController : ControllerBase
{
    private readonly ICatalogBrowseService _catalogBrowseService;
    private readonly IIssuersService _issuersService;

    public CatalogController(ICatalogBrowseService catalogBrowseService, IIssuersService issuersService)
    {
        _catalogBrowseService = catalogBrowseService;
        _issuersService = issuersService;
    }

    [HttpGet("issuer-browser")]
    public async Task<ActionResult<IEnumerable<IssuerTreeDto>>> GetIssuerBrowser()
    {
        var result = await _issuersService.GetIssuerHierarchyAsync();
        return Ok(result);
    }

    [HttpGet("ruler-browser")]
    public async Task<ActionResult<IEnumerable<CatalogIssuerRulerNodeDto>>> GetRulerBrowser(CancellationToken cancellationToken)
    {
        var result = await _catalogBrowseService.GetRulerBrowserAsync(cancellationToken);
        return Ok(result);
    }
}
