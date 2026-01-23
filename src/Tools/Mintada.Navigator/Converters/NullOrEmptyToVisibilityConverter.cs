using System;
using System.Collections;
using System.Globalization;
using System.Windows;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class NullOrEmptyToVisibilityConverter : IValueConverter
    {
        public static NullOrEmptyToVisibilityConverter Instance { get; } = new NullOrEmptyToVisibilityConverter();

        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null)
                return Visibility.Visible;

            if (value is ICollection collection && collection.Count == 0)
                return Visibility.Visible;

            if (value is IEnumerable enumerable && !enumerable.GetEnumerator().MoveNext())
                return Visibility.Visible;

            return Visibility.Collapsed;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
