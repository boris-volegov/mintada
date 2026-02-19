using Mintada.Mcp.Postgres;
using ModelContextProtocol.Server;

var builder = WebApplication.CreateBuilder(args);

if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("ASPNETCORE_URLS")))
{
    builder.WebHost.UseUrls("http://0.0.0.0:8080");
}

builder.Services
    .AddMcpServer()
    .WithHttpTransport()
    .WithTools<SqlMcpTools>();

var app = builder.Build();

app.MapGet("/", () => Results.Ok(new
{
    name = "postgres-mcp",
    status = "ok"
}));

app.MapMcp("/mcp-postgres");
app.MapMcp("/mcp");

app.Run();
