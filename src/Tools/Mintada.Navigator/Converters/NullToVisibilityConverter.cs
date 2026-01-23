using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class NullToVisibilityConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            bool isNull = value == null || (value is string str && string.IsNullOrWhiteSpace(str));
            bool inverse = parameter is string param && param == "Inverse";
            
            if (inverse)
            {
                return isNull ? Visibility.Visible : Visibility.Collapsed;
            }
            else
            {
                return isNull ? Visibility.Collapsed : Visibility.Visible;
            }
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
