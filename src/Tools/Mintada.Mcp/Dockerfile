# Build stage
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["src/Tools/Mintada.Mcp/Mintada.Mcp.csproj", "Mintada.Mcp/"]
RUN dotnet restore "Mintada.Mcp/Mintada.Mcp.csproj"
COPY src/Tools/Mintada.Mcp/ Mintada.Mcp/
WORKDIR "/src/Mintada.Mcp"
RUN dotnet build "Mintada.Mcp.csproj" -c Release -o /app/build
RUN dotnet publish "Mintada.Mcp.csproj" -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://0.0.0.0:8080
EXPOSE 8080

ENTRYPOINT ["dotnet", "Mintada.Mcp.dll"]
