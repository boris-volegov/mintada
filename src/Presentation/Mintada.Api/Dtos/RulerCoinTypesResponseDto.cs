namespace Mintada.Api.Dtos;

public class RulerCoinTypesResponseDto
{
    public int RulerId { get; set; }
    public string RulerName { get; set; } = string.Empty;
    public string? PortraitUrl { get; set; }
    public string? InfoHtml { get; set; }
    public bool HasMultipleIssuers { get; set; }
    public List<RulerIssuerCoinTypeGroupDto> IssuerGroups { get; set; } = new();
}
