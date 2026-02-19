using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issue_types")]
public class IssueType : BaseEntity
{
    public string Name { get; set; } = null!;
}
