# Build stage
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["src/Tools/Mintada.Mcp.Postgres/Mintada.Mcp.Postgres.csproj", "Mintada.Mcp.Postgres/"]
RUN dotnet restore "Mintada.Mcp.Postgres/Mintada.Mcp.Postgres.csproj"
COPY src/Tools/Mintada.Mcp.Postgres/ Mintada.Mcp.Postgres/
WORKDIR "/src/Mintada.Mcp.Postgres"
RUN dotnet build "Mintada.Mcp.Postgres.csproj" -c Release -o /app/build
RUN dotnet publish "Mintada.Mcp.Postgres.csproj" -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://0.0.0.0:8080
EXPOSE 8080

ENTRYPOINT ["dotnet", "Mintada.Mcp.Postgres.dll"]
