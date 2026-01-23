using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Mintada.Data;

public class MintadaDbContextFactory : IDesignTimeDbContextFactory<MintadaDbContext>
{
    public MintadaDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<MintadaDbContext>();
        // Using localhost because this factory runs on the host machine during development
        optionsBuilder.UseNpgsql("Host=localhost;Port=5432;Database=mintada_db;Username=admin;Password=mintada");

        return new MintadaDbContext(optionsBuilder.Options);
    }
}
