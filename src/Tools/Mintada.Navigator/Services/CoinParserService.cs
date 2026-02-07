using HtmlAgilityPack;
using Mintada.Navigator.Models;
using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace Mintada.Navigator.Services
{
    public class CoinParserService
    {
        private static readonly Regex RulerIdRegex = new(@"[?&]id=(\d+)\b", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        public ParsedCoinData Parse(string htmlContent)
        {
            var doc = new HtmlDocument();
            doc.LoadHtml(htmlContent);

            var data = new ParsedCoinData();

            // 1. Title
            var h1 = doc.DocumentNode.SelectSingleNode("//*[@id='main_title']//h1");
            if (h1 != null)
            {
                // We just want the text, ignoring the subtitle span
                var span = h1.SelectSingleNode("span");
                if (span != null)
                {
                    span.Remove();
                }
                data.Title = h1.InnerText.Trim();
            }

            // 2. Denomination (Value + Currency)
            string? valueText = null;
            string? currencyText = null;

            var featuresRows = doc.DocumentNode.SelectNodes("//*[@id='fiche_caracteristiques']//table//tr");
            if (featuresRows != null)
            {
                foreach (var row in featuresRows)
                {
                    var th = row.SelectSingleNode("th");
                    var td = row.SelectSingleNode("td");
                    if (th == null || td == null) continue;

                    string label = th.InnerText.Trim().ToLower().TrimEnd(':');
                    
                    // Normalize whitespace: replace newlines/tabs with single space
                    string rawValue = td.InnerText;
                    string value = Regex.Replace(rawValue, @"\s+", " ").Trim();
                    
                    // Normalize label key
                    string key = Regex.Replace(label, @"[^a-z0-9]+", "_").Trim('_');

                    if (key == "value")
                    {
                        valueText = value;
                    }
                    else if (key == "currency")
                    {
                        currencyText = value;
                    }
                }
            }

            // Construct Denomination Text
            if (!string.IsNullOrEmpty(valueText) && !string.IsNullOrEmpty(currencyText))
            {
                data.DenominationText = $"{valueText} {currencyText}";
            }
            else if (!string.IsNullOrEmpty(valueText))
            {
                data.DenominationText = valueText;
            }
            else if (!string.IsNullOrEmpty(currencyText))
            {
                data.DenominationText = currencyText;
            }

            return data;
        }

        public List<RulerOption> ExtractRulers(string htmlContent)
        {
            var rulers = new List<RulerOption>();
            if (string.IsNullOrWhiteSpace(htmlContent))
            {
                return rulers;
            }

            var doc = new HtmlDocument();
            doc.LoadHtml(htmlContent);

            var scope = doc.DocumentNode.SelectSingleNode("//*[@id='fiche_caracteristiques']") ?? doc.DocumentNode;
            var rows = scope.SelectNodes(".//tr");
            if (rows == null)
            {
                return rulers;
            }

            var seen = new HashSet<string>(StringComparer.Ordinal);

            foreach (var row in rows)
            {
                var links = row.SelectNodes(".//a[contains(@href,'/catalogue/ruler.php?id=')]");
                if (links == null)
                {
                    continue;
                }

                foreach (var link in links)
                {
                    var href = link.GetAttributeValue("href", string.Empty);
                    var match = RulerIdRegex.Match(href);
                    if (!match.Success || !long.TryParse(match.Groups[1].Value, out var rulerId))
                    {
                        continue;
                    }

                    var rulerName = CleanText(link.InnerText);
                    if (string.IsNullOrWhiteSpace(rulerName))
                    {
                        continue;
                    }

                    var dedupeKey = $"{rulerId}|{rulerName}";
                    if (!seen.Add(dedupeKey))
                    {
                        continue;
                    }

                    rulers.Add(new RulerOption
                    {
                        Id = rulerId,
                        Name = rulerName
                    });
                }
            }

            return rulers;
        }

        private static string CleanText(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return string.Empty;
            }

            var text = HtmlEntity.DeEntitize(value);
            text = text.Replace('\u00A0', ' ')
                       .Replace('\u202F', ' ')
                       .Replace('\u2009', ' ')
                       .Replace('\u2007', ' ')
                       .Replace('\u2060', ' ')
                       .Replace('\uFEFF', ' ')
                       .Replace('\u2044', '/');

            return Regex.Replace(text, @"\s+", " ").Trim();
        }
    }
}
