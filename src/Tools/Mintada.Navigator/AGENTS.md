# Mintada.Navigator Agent Rules

## Publish After Modifications

- After each code modification in `src/Tools/Mintada.Navigator`, run:
  - `dotnet publish src/Tools/Mintada.Navigator/Mintada.Navigator.csproj -c Release -o src/Tools/Mintada.Navigator/publish`
- Treat publish success as required validation before considering the task complete.
