namespace Mintada.Api.Dtos;

public class IssuerDto
{
    public int Id { get; set; }
    public int? ParentId { get; set; }
    public string? Url { get; set; }
    public string? Name { get; set; }
    public string? UrlSlug { get; set; }
    public string? TerritoryType { get; set; }
    public bool IsHistoricalPeriod { get; set; }
    public bool IsSection { get; set; }
}
