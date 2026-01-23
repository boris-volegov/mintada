using Mintada.Api.Dtos;

namespace Mintada.Api.Services;

public interface IIssuersService
{
    Task<IEnumerable<IssuerTreeDto>> GetIssuerHierarchyAsync();
}
