namespace Mintada.Api.Dtos;

public class IssuerTreeDto : IssuerDto
{
    public List<IssuerTreeDto> Children { get; set; } = new();
}
