namespace Mintada.Api.Dtos;

public class CatalogIssuerRulerNodeDto : IssuerDto
{
    public List<CatalogIssuerRulerNodeDto> Children { get; set; } = new();
    public List<CatalogRulerDto> Rulers { get; set; } = new();

    // Number of leaf issuers in this subtree that have at least one ruler.
    public int LeafIssuerCountWithRulers { get; set; }

    // Total number of ruler items across leaf issuers in this subtree.
    public int RulerCountInSubtree { get; set; }
}

