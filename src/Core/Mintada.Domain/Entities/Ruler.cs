using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("rulers")]
public class Ruler : BaseEntity
{
    public string Name { get; set; } = null!;
    public string? PortraitUrl { get; set; }
    public string? Info { get; set; }
}
