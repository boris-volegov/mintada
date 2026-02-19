using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("shapes")]
public class Shape : BaseEntity
{
    public string Name { get; set; } = null!;
    public int SeqNumber { get; set; }
}
