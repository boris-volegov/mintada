using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class TabIndexToVisibilityConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is int currentIndex)
            {
                int targetIndex = -1;
                
                if (parameter is int pInt)
                {
                    targetIndex = pInt;
                }
                else if (parameter is string pStr && int.TryParse(pStr, out int pParsed))
                {
                    targetIndex = pParsed;
                }

                if (targetIndex != -1)
                {
                     return currentIndex == targetIndex ? Visibility.Visible : Visibility.Collapsed;
                }
            }
            return Visibility.Collapsed;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
