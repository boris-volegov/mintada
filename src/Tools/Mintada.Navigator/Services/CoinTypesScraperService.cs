using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;

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
        private static readonly HttpClient _httpClient = new()
        {
            Timeout = TimeSpan.FromSeconds(20)
        };

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

        public async Task<(string IssuerName, string IssuerSlug)?> TryResolveIssuerFromCoinTypeIdAsync(
            long coinTypeId,
            CancellationToken cancellationToken = default)
        {
            if (coinTypeId <= 0)
            {
                return null;
            }

            var resolverScriptPath = Path.Combine(
                Path.GetDirectoryName(_scraperScriptPath) ?? Environment.CurrentDirectory,
                "resolve_coin_type_issuer.py");
            if (File.Exists(_pythonPath) && File.Exists(resolverScriptPath))
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = _pythonPath,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WorkingDirectory = Path.GetDirectoryName(resolverScriptPath) ?? Environment.CurrentDirectory
                };

                startInfo.ArgumentList.Add(resolverScriptPath);
                startInfo.ArgumentList.Add("--coin-type-id");
                startInfo.ArgumentList.Add(coinTypeId.ToString(CultureInfo.InvariantCulture));

                using var process = new Process { StartInfo = startInfo };
                process.Start();

                var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
                var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

                await process.WaitForExitAsync(cancellationToken);
                var stdout = (await stdoutTask).Trim();
                _ = await stderrTask;

                if (process.ExitCode == 0 && !string.IsNullOrWhiteSpace(stdout))
                {
                    var jsonLine = stdout
                        .Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
                        .LastOrDefault();
                    if (!string.IsNullOrWhiteSpace(jsonLine))
                    {
                        try
                        {
                            using var doc = JsonDocument.Parse(jsonLine);
                            if (doc.RootElement.TryGetProperty("issuer_name", out var issuerNameProp) &&
                                doc.RootElement.TryGetProperty("issuer_slug", out var issuerSlugProp))
                            {
                                var issuerName = issuerNameProp.GetString()?.Trim() ?? string.Empty;
                                var issuerSlug = issuerSlugProp.GetString()?.Trim() ?? string.Empty;
                                if (!string.IsNullOrWhiteSpace(issuerName) && !string.IsNullOrWhiteSpace(issuerSlug))
                                {
                                    return (issuerName, issuerSlug);
                                }
                            }
                        }
                        catch
                        {
                            // Fallback to HTTP parser below.
                        }
                    }
                }
            }

            try
            {
                var requestUri = $"https://en.numista.com/{coinTypeId}";
                using var response = await _httpClient.GetAsync(requestUri, cancellationToken);
                if (!response.IsSuccessStatusCode)
                {
                    return null;
                }

                var html = await response.Content.ReadAsStringAsync(cancellationToken);
                if (string.IsNullOrWhiteSpace(html))
                {
                    return null;
                }

                var sectionMatch = Regex.Match(
                    html,
                    "<section[^>]*id\\s*=\\s*[\"']fiche_caracteristiques[\"'][^>]*>(?<section>.*?)</section>",
                    RegexOptions.IgnoreCase | RegexOptions.Singleline);
                if (!sectionMatch.Success)
                {
                    return null;
                }

                var sectionHtml = sectionMatch.Groups["section"].Value;
                var issuerRowMatch = Regex.Match(
                    sectionHtml,
                    "<tr[^>]*>\\s*<th[^>]*>\\s*Issuer\\s*</th>\\s*<td[^>]*>(?<td>.*?)</td>\\s*</tr>",
                    RegexOptions.IgnoreCase | RegexOptions.Singleline);
                if (!issuerRowMatch.Success)
                {
                    return null;
                }

                var tdHtml = issuerRowMatch.Groups["td"].Value;
                var linkMatch = Regex.Match(
                    tdHtml,
                    "<a[^>]*href\\s*=\\s*[\"'](?<href>[^\"']+)[\"'][^>]*>(?<text>.*?)</a>",
                    RegexOptions.IgnoreCase | RegexOptions.Singleline);
                if (!linkMatch.Success)
                {
                    return null;
                }

                var href = linkMatch.Groups["href"].Value.Trim();
                var issuerNameRaw = linkMatch.Groups["text"].Value;
                var issuerName = WebUtility.HtmlDecode(Regex.Replace(issuerNameRaw, "<.*?>", string.Empty)).Trim();
                if (string.IsNullOrWhiteSpace(issuerName))
                {
                    return null;
                }

                var slugMatch = Regex.Match(
                    href,
                    "/catalogue/(?<slug>.+?)-\\d+\\.html?$",
                    RegexOptions.IgnoreCase);
                if (!slugMatch.Success)
                {
                    return null;
                }

                var issuerSlug = slugMatch.Groups["slug"].Value.Trim();
                if (string.IsNullOrWhiteSpace(issuerSlug))
                {
                    return null;
                }

                return (issuerName, issuerSlug);
            }
            catch
            {
                return null;
            }
        }
    }
}
