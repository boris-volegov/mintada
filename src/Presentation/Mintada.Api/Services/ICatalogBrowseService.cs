using Mintada.Api.Dtos;

namespace Mintada.Api.Services;

public interface ICatalogBrowseService
{
    Task<IEnumerable<CatalogIssuerRulerNodeDto>> GetRulerBrowserAsync(CancellationToken cancellationToken = default);
}

