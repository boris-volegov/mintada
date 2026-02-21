using System;
using System.Globalization;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class StringEqualityConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            var left = values.Length > 0 && values[0] != null ? values[0].ToString() : null;
            var right = values.Length > 1 && values[1] != null ? values[1].ToString() : null;

            var leftValue = Normalize(left);
            var rightValue = Normalize(right);

            return string.Equals(leftValue, rightValue, StringComparison.OrdinalIgnoreCase);
        }

        private static string Normalize(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return string.Empty;
            }

            return value.Trim();
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
