namespace Mintada.Api.Dtos;

public class CatalogRulerDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? RuleType { get; set; }
    public string? Title { get; set; }
    public int? GroupId { get; set; }
    public string? GroupName { get; set; }
}
