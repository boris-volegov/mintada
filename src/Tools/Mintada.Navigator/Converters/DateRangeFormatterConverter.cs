using System;
using System.Globalization;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class DateRangeFormatterConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            var start = values.Length > 0 && values[0] != null ? values[0].ToString()?.Trim() ?? string.Empty : string.Empty;
            var end = values.Length > 1 && values[1] != null ? values[1].ToString()?.Trim() ?? string.Empty : string.Empty;

            if (string.IsNullOrWhiteSpace(start) && string.IsNullOrWhiteSpace(end))
            {
                return string.Empty;
            }

            if (string.IsNullOrWhiteSpace(start))
            {
                return end;
            }

            if (string.IsNullOrWhiteSpace(end) || string.Equals(start, end, StringComparison.OrdinalIgnoreCase))
            {
                return start;
            }

            return $"{start} - {end}";
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
