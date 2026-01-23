using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("coin_type_samples")]
public class CoinTypeSample : BaseEntity
{
    public int CoinTypeId { get; set; }
    public CoinType CoinType { get; set; } = null!;

    public string? ObverseImage { get; set; }
    public string? ReverseImage { get; set; }
    
    public int SampleType { get; set; }
}
