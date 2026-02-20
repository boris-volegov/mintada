namespace Mintada.Api.Dtos;

public class RulerIssuerCoinTypeGroupDto
{
    public int IssuerId { get; set; }
    public string? IssuerName { get; set; }
    public string? IssuerUrlSlug { get; set; }
    public string? TerritoryType { get; set; }

    public List<RulerCoinTypeItemDto> CoinTypes { get; set; } = new();
}
