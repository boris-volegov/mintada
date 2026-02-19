using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("calendar_systems")]
public class CalendarSystem : BaseEntity
{
    public string Name { get; set; } = null!;
}
