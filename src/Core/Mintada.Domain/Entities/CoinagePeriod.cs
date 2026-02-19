using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("coinage_periods")]
public class CoinagePeriod : BaseEntity
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public string? Name { get; set; }
    public string? UnitRelationText { get; set; }
}
