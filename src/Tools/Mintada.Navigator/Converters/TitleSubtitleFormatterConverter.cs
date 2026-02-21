using System;
using System.Globalization;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class TitleSubtitleFormatterConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            var title = values.Length > 0 && values[0] != null ? values[0].ToString() ?? string.Empty : string.Empty;
            var subtitle = values.Length > 1 && values[1] != null ? values[1].ToString() ?? string.Empty : string.Empty;
            var trimmedSubtitle = subtitle.Trim();

            if (string.IsNullOrWhiteSpace(trimmedSubtitle))
            {
                return title;
            }

            if (string.IsNullOrWhiteSpace(title))
            {
                return trimmedSubtitle;
            }

            return $"{title} ({trimmedSubtitle})";
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
