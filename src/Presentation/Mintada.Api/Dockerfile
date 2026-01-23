FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy solution and project files first for caching
COPY ["Mintada.slnx", "./"]
COPY ["Presentation/Mintada.Api/Mintada.Api.csproj", "Presentation/Mintada.Api/"]
COPY ["Infrastructure/Mintada.Data/Mintada.Data.csproj", "Infrastructure/Mintada.Data/"]
COPY ["Core/Mintada.Domain/Mintada.Domain.csproj", "Core/Mintada.Domain/"]
COPY ["Tools/Mintada.Migrator/Mintada.Migrator.csproj", "Tools/Mintada.Migrator/"]

# Restore dependencies
RUN dotnet restore "Presentation/Mintada.Api/Mintada.Api.csproj"

# Copy the rest of the source code
COPY . .

# Build and Publish
WORKDIR "/src/Presentation/Mintada.Api"
RUN dotnet publish "Mintada.Api.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Final Stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet", "Mintada.Api.dll"]
