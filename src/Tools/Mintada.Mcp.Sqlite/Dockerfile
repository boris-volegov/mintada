# Build stage
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["src/Tools/Mintada.Mcp.Sqlite/Mintada.Mcp.Sqlite.csproj", "Mintada.Mcp.Sqlite/"]
RUN dotnet restore "Mintada.Mcp.Sqlite/Mintada.Mcp.Sqlite.csproj"
COPY src/Tools/Mintada.Mcp.Sqlite/ Mintada.Mcp.Sqlite/
WORKDIR "/src/Mintada.Mcp.Sqlite"
RUN dotnet build "Mintada.Mcp.Sqlite.csproj" -c Release -o /app/build
RUN dotnet publish "Mintada.Mcp.Sqlite.csproj" -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://0.0.0.0:8080
EXPOSE 8080

ENTRYPOINT ["dotnet", "Mintada.Mcp.Sqlite.dll"]
