using Microsoft.EntityFrameworkCore;
using Mintada.Domain.Entities;

namespace Mintada.Data;

public class MintadaDbContext : DbContext
{
    public DbSet<Issuer> Issuers { get; set; }
    public DbSet<IssuerAltName> IssuerAltNames { get; set; }
    public DbSet<IssuerType> IssuerTypes { get; set; }
    public DbSet<Ruler> Rulers { get; set; }
    public DbSet<IssuersRulersRelGroup> IssuersRulersRelGroups { get; set; }
    public DbSet<IssuersRulersRel> IssuersRulersRel { get; set; }
    public DbSet<CoinTypesIssuersRulersRel> CoinTypesIssuersRulersRel { get; set; }
    public DbSet<Shape> Shapes { get; set; }
    public DbSet<CoinagePeriod> CoinagePeriods { get; set; }
    public DbSet<IssueType> IssueTypes { get; set; }
    public DbSet<IssuerIssueTypeRel> IssuerIssueTypesRel { get; set; }
    public DbSet<CalendarSystem> CalendarSystems { get; set; }
    public DbSet<CoinType> CoinTypes { get; set; }
    public DbSet<CoinTypeSample> CoinTypeSamples { get; set; }

    public MintadaDbContext(DbContextOptions<MintadaDbContext> options) : base(options)
    {
    }
    
    // Additional configuration if needed
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        
        // Example config
        modelBuilder.Entity<CoinType>()
            .Property(c => c.Title)
            .HasColumnType("text"); // Explicitly ensure text

        modelBuilder.Entity<IssuerIssueTypeRel>()
            .HasKey(x => new { x.IssuerId, x.IssueTypeId });

        modelBuilder.Entity<IssuerIssueTypeRel>()
            .HasOne(x => x.Issuer)
            .WithMany()
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<IssuerIssueTypeRel>()
            .HasOne(x => x.IssueType)
            .WithMany()
            .HasForeignKey(x => x.IssueTypeId)
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<IssuerAltName>()
            .HasKey(x => new { x.IssuerId, x.AltName });

        modelBuilder.Entity<IssuerAltName>()
            .HasOne(x => x.Issuer)
            .WithMany(i => i.AltNames)
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<Issuer>()
            .HasOne(i => i.IssuerType)
            .WithMany()
            .HasForeignKey(i => i.IssuerTypeId)
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<CoinagePeriod>()
            .HasOne(x => x.Issuer)
            .WithMany()
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<CoinType>()
            .HasOne(x => x.Issuer)
            .WithMany(i => i.CoinTypes)
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<IssuersRulersRelGroup>()
            .HasOne(x => x.Issuer)
            .WithMany()
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<IssuersRulersRelGroup>()
            .HasAlternateKey(x => new { x.Id, x.IssuerId });

        modelBuilder.Entity<IssuersRulersRel>()
            .HasOne(x => x.Issuer)
            .WithMany()
            .HasForeignKey(x => x.IssuerId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<IssuersRulersRel>()
            .HasOne(x => x.Ruler)
            .WithMany()
            .HasForeignKey(x => x.RulerId)
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<IssuersRulersRel>()
            .HasOne(x => x.Group)
            .WithMany(g => g.RulerRelations)
            .HasForeignKey(x => new { x.GroupId, x.IssuerId })
            .HasPrincipalKey(g => new { g.Id, g.IssuerId })
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<CoinTypesIssuersRulersRel>()
            .HasKey(x => new { x.CoinTypeId, x.IssuerRulerRelId });

        modelBuilder.Entity<CoinTypesIssuersRulersRel>()
            .HasOne(x => x.CoinType)
            .WithMany(ct => ct.IssuerRulerRelations)
            .HasForeignKey(x => x.CoinTypeId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<CoinTypesIssuersRulersRel>()
            .HasOne(x => x.IssuerRulerRel)
            .WithMany(rel => rel.CoinTypeRelations)
            .HasForeignKey(x => x.IssuerRulerRelId)
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<CoinTypeSample>()
            .HasOne(x => x.CoinType)
            .WithMany(ct => ct.Samples)
            .HasForeignKey(x => x.CoinTypeId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<CoinType>()
            .HasOne(ct => ct.IssuerIssueType)
            .WithMany(rel => rel.CoinTypes)
            .HasForeignKey(ct => new { ct.IssuerId, ct.IssueTypeId })
            .HasPrincipalKey(rel => new { rel.IssuerId, rel.IssueTypeId })
            .OnDelete(DeleteBehavior.Restrict);

        // Issuer Self-Referencing Relationship
        modelBuilder.Entity<Issuer>()
            .HasOne(i => i.Parent)
            .WithMany(i => i.Children)
            .HasForeignKey(i => i.ParentId)
            .OnDelete(DeleteBehavior.Restrict);

    }
}
