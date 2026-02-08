using System.Diagnostics;
using System.Globalization;
using System.IO;

namespace Mintada.Navigator.Services
{
    public sealed class CoinTypesScraperRunResult
    {
        public int ExitCode { get; init; }
        public string StandardOutput { get; init; } = string.Empty;
        public string StandardError { get; init; } = string.Empty;
    }

    public class CoinTypesScraperService
    {
        private readonly string _pythonPath;
        private readonly string _scraperScriptPath;

        public CoinTypesScraperService(string pythonPath, string scraperScriptPath)
        {
            _pythonPath = pythonPath;
            _scraperScriptPath = scraperScriptPath;
        }

        public async Task<CoinTypesScraperRunResult> ScrapeCoinTypeAsync(
            long coinTypeId,
            string? issuerUrlSlug = null,
            int? page = null,
            string? cookie = null,
            CancellationToken cancellationToken = default)
        {
            if (!File.Exists(_pythonPath))
            {
                throw new FileNotFoundException($"Python executable was not found at '{_pythonPath}'.");
            }

            if (!File.Exists(_scraperScriptPath))
            {
                throw new FileNotFoundException($"Scraper script was not found at '{_scraperScriptPath}'.");
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = _pythonPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = Path.GetDirectoryName(_scraperScriptPath) ?? Environment.CurrentDirectory
            };

            startInfo.ArgumentList.Add(_scraperScriptPath);
            startInfo.ArgumentList.Add("--coin-type-id");
            startInfo.ArgumentList.Add(coinTypeId.ToString(CultureInfo.InvariantCulture));

            if (!string.IsNullOrWhiteSpace(issuerUrlSlug))
            {
                startInfo.ArgumentList.Add("--issuer-url-slug");
                startInfo.ArgumentList.Add(issuerUrlSlug.Trim());
            }

            if (page.HasValue)
            {
                startInfo.ArgumentList.Add("--page");
                startInfo.ArgumentList.Add(page.Value.ToString(CultureInfo.InvariantCulture));
            }

            if (!string.IsNullOrWhiteSpace(cookie))
            {
                var normalizedCookie = cookie
                    .Replace("\r\n", " ")
                    .Replace('\n', ' ')
                    .Replace('\r', ' ')
                    .Trim();

                if (!string.IsNullOrWhiteSpace(normalizedCookie))
                {
                    startInfo.Environment["NUMISTA_COOKIE"] = normalizedCookie;
                }
            }

            using var process = new Process { StartInfo = startInfo };
            process.Start();

            var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
            var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

            await process.WaitForExitAsync(cancellationToken);

            return new CoinTypesScraperRunResult
            {
                ExitCode = process.ExitCode,
                StandardOutput = await stdoutTask,
                StandardError = await stderrTask
            };
        }
    }
}
