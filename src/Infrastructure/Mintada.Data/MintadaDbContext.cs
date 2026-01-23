using Microsoft.EntityFrameworkCore;
using Mintada.Domain.Entities;

namespace Mintada.Data;

public class MintadaDbContext : DbContext
{
    public DbSet<Issuer> Issuers { get; set; }
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

        // Issuer Self-Referencing Relationship
        modelBuilder.Entity<Issuer>()
            .HasOne(i => i.Parent)
            .WithMany(i => i.Children)
            .HasForeignKey(i => i.ParentId)
            .OnDelete(DeleteBehavior.Restrict);

        modelBuilder.Entity<Issuer>()
             .HasOne(i => i.TopParent)
             .WithMany() // No inverse collection for TopParent
             .HasForeignKey(i => i.TopParentId)
             .OnDelete(DeleteBehavior.Restrict);

    }
}
