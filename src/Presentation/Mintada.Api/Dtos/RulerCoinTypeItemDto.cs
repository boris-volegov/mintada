namespace Mintada.Api.Dtos;

public class RulerCoinTypeItemDto
{
    public int Id { get; set; }
    public string Title { get; set; } = null!;
    public string? Subtitle { get; set; }
    public string? Period { get; set; }
    public int? RarityIndex { get; set; }
    public string CoinTypeSlug { get; set; } = null!;
    public DateTime DateTimeInserted { get; set; }
    public int IssueTypeId { get; set; }
    public string? ObverseImage { get; set; }
    public string? ReverseImage { get; set; }
}
