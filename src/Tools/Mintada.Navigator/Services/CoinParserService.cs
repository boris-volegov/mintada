using HtmlAgilityPack;
using Mintada.Navigator.Models;
using System;
using System.Linq;
using System.Text.RegularExpressions;

namespace Mintada.Navigator.Services
{
    public class CoinParserService
    {
        public ParsedCoinData Parse(string htmlContent)
        {
            var doc = new HtmlDocument();
            doc.LoadHtml(htmlContent);

            var data = new ParsedCoinData();

            // 1. Title and Subtitle
            var h1 = doc.DocumentNode.SelectSingleNode("//*[@id='main_title']//h1");
            if (h1 != null)
            {
                var span = h1.SelectSingleNode("span");
                if (span != null)
                {
                    data.Subtitle = span.InnerText.Trim();
                    // Remove span to get just the title part
                    span.Remove();
                }
                data.Title = h1.InnerText.Trim();
            }

            // 2. Features Table
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
                    
                    // Check for Ruler ID in this cell
                    var rulerLink = td.SelectSingleNode(".//a[contains(@href, 'ruler.php')]");
                    if (rulerLink != null)
                    {
                        var href = rulerLink.GetAttributeValue("href", "");
                        var match = Regex.Match(href, @"id=(\d+)");
                        if (match.Success && int.TryParse(match.Groups[1].Value, out int rid))
                        {
                            data.RulerId = rid;
                        }
                    }

                    // Normalize label key similar to Python script
                    string key = Regex.Replace(label, @"[^a-z0-9]+", "_").Trim('_');

                    switch (key)
                    {
                        case "issuer":
                            data.Issuer = value;
                            break;
                        case "type":
                            // Standard circulation coin, etc. - maybe needed?
                            break;
                        case "year":
                        case "years":
                            data.YearText = value;
                            break;
                        case "value":
                            data.ValueText = value;
                            break;
                        case "currency":
                            data.CurrencyText = value;
                            break;
                        case "composition":
                            data.Composition = value;
                            break;
                        case "weight":
                            data.WeightText = value;
                            break;
                        case "diameter":
                            data.DiameterText = value;
                            break;
                        case "thickness":
                            data.ThicknessText = value;
                            break;
                        case "shape":
                            data.Shape = value;
                            break;
                        case "orientation":
                            data.Orientation = value;
                            break;
                         case "references":
                             // Clean up tooltips if any
                             var tooltips = td.SelectNodes(".//div[contains(@class,'tooltip')]");
                             if (tooltips != null)
                             {
                                 foreach (var t in tooltips) t.Remove();
                             }
                             data.References = td.InnerText.Trim();
                             break;
                    }
                }
            }
            
            // 3. Validate Dimensions
            ValidateDimensions(data);

            return data;
        }

        private void ValidateDimensions(ParsedCoinData data)
        {
            var alarmMessages = new System.Collections.Generic.List<string>();

            // Weight (expected 'g')
            if (!string.IsNullOrWhiteSpace(data.WeightText))
            {
                var (val, unit) = ParseValueAndUnit(data.WeightText);
                if (val.HasValue)
                {
                    if (unit.Equals("g", StringComparison.OrdinalIgnoreCase))
                        data.DecimalWeight = val.Value;
                    else
                        alarmMessages.Add($"Weight unit mismatch: expected 'g', got '{unit}'");
                }
            }

            // Diameter (expected 'mm')
            if (!string.IsNullOrWhiteSpace(data.DiameterText))
            {
                var (val, unit) = ParseValueAndUnit(data.DiameterText);
                if (val.HasValue)
                {
                    if (unit.Equals("mm", StringComparison.OrdinalIgnoreCase))
                        data.DecimalDiameter = val.Value;
                    else
                        alarmMessages.Add($"Diameter unit mismatch: expected 'mm', got '{unit}'");
                }
            }

            // Thickness (expected 'mm')
            if (!string.IsNullOrWhiteSpace(data.ThicknessText))
            {
                var (val, unit) = ParseValueAndUnit(data.ThicknessText);
                if (val.HasValue)
                {
                    if (unit.Equals("mm", StringComparison.OrdinalIgnoreCase))
                        data.DecimalThickness = val.Value;
                    else
                        alarmMessages.Add($"Thickness unit mismatch: expected 'mm', got '{unit}'");
                }
            }

            if (alarmMessages.Count > 0)
            {
                data.HasDimensionAlarm = true;
                data.DimensionAlarmMessage = string.Join("; ", alarmMessages);
            }
        }

        private (decimal? value, string unit) ParseValueAndUnit(string raw)
        {
            // Matches number (int or decimal) followed by optional space and unit text
            var match = Regex.Match(raw, @"([\d\.,]+)\s*([a-zA-Z]+)");
            if (match.Success)
            {
                string numStr = match.Groups[1].Value.Replace(',', '.'); // Normalize decimal separator
                if (decimal.TryParse(numStr, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out decimal val))
                {
                    string unit = match.Groups[2].Value;
                    return (val, unit);
                }
            }
            return (null, string.Empty);
        }
    }
}
