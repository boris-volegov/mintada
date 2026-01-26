using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;

namespace Mintada.Navigator.Services
{
    public class ImageAnalysisService
    {
        private readonly System.Collections.Concurrent.ConcurrentDictionary<string, ulong> _dHashCache = new();

        public async Task<ulong?> ComputeDHashAsync(string imagePath)
        {
            if (string.IsNullOrEmpty(imagePath) || !File.Exists(imagePath)) return null;

            if (_dHashCache.TryGetValue(imagePath, out ulong cachedHash))
            {
                return cachedHash;
            }

            // Perform image analysis on the calling thread (assumed background)
            try
            {
                return await Task.Run(() => 
                {
                    try 
                    {
                        var bitmap = new BitmapImage();
                        bitmap.BeginInit();
                        bitmap.UriSource = new Uri(imagePath);
                        bitmap.DecodePixelWidth = 9;   // 9 columns
                        bitmap.DecodePixelHeight = 8;  // 8 rows
                        bitmap.CacheOption = BitmapCacheOption.OnLoad;
                        bitmap.EndInit();
                        bitmap.Freeze(); 

                        int width = 9;
                        int height = 8;
                        int stride = width * 4; // 32bpp usually
                        byte[] pixels = new byte[height * stride];
                        bitmap.CopyPixels(pixels, stride, 0);

                        // 1. Calculate brightness for all pixels (9x8 = 72 pixels)
                        double[] brightnessValues = new double[width * height];
                        for (int y = 0; y < height; y++)
                        {
                            for (int x = 0; x < width; x++)
                            {
                                int idx = (y * stride) + (x * 4);
                                // Standard luma: 0.299R + 0.587G + 0.114B
                                double b = (pixels[idx+2] * 0.299) + (pixels[idx+1] * 0.587) + (pixels[idx] * 0.114);
                                brightnessValues[(y * width) + x] = b;
                            }
                        }

                        // 2. Perform Histogram Contrast Stretching (AutoContrast) with Clipping
                        var sortedCpy = (double[])brightnessValues.Clone();
                        Array.Sort(sortedCpy);

                        // Clip bottom and top 5% (approx 3-4 pixels out of 72)
                        int clipCount = (int)(brightnessValues.Length * 0.05); 
                        double min = sortedCpy[clipCount];
                        double max = sortedCpy[brightnessValues.Length - 1 - clipCount];
                        double range = max - min;
                        
                        if (range < 1) range = 1; // Avoid divide by zero

                        for(int i=0; i < brightnessValues.Length; i++)
                        {
                            double val = brightnessValues[i];
                            if (val < min) val = min;
                            if (val > max) val = max;
                            
                            // Normalize to 0-255 (though relative order is enough, clipping matters)
                            brightnessValues[i] = (val - min) / range * 255.0;
                        }

                        ulong hash = 0;
                        
                        for (int y = 0; y < 8; y++)
                        {
                            for (int x = 0; x < 8; x++)
                            {
                                // 3. Compute Hash
                                double b1 = brightnessValues[(y * width) + x];
                                double b2 = brightnessValues[(y * width) + (x + 1)];
                                
                                if (b1 > b2)
                                {
                                    hash |= (1UL << ((y * 8) + x));
                                }
                            }
                        }
                        
                        _dHashCache.TryAdd(imagePath, hash);
                        return (ulong?)hash;
                    } 
                    catch 
                    {
                        return null;
                    }
                });
            }
            catch
            {
                return null;
            }
        }

        public int CalculateHammingDistance(ulong hash1, ulong hash2)
        {
            ulong xor = hash1 ^ hash2;
            int distance = 0;
            while (xor > 0)
            {
                distance += (int)(xor & 1);
                xor >>= 1;
            }
            return distance;
        }
    }
}
