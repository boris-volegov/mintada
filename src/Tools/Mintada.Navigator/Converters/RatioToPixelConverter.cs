using System;
using System.Globalization;
using System.Windows.Data;

namespace Mintada.Navigator.Converters
{
    public class RatioToPixelConverter : IMultiValueConverter
    {
        public static readonly RatioToPixelConverter Instance = new RatioToPixelConverter();

        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            if (values.Length >= 2 && values[0] is double width && values[1] is double ratio)
            {
                double offset = 0;
                if (values.Length > 2 && values[2] != null) // Check for optional 3rd offset
                {
                   double.TryParse(values[2].ToString(), out offset);
                }
                return (width * ratio) + offset;
            }
            return 0.0;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
