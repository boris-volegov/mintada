using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Media.Imaging;

namespace Mintada.Navigator.Services
{
    public class FileService
    {
        private readonly string _basePath;

        public FileService(string basePath)
        {
            _basePath = basePath;
        }

        public string GetCoinDirectory(string issuerSlug, string coinSlug, long coinId)
        {
            var folderName = $"{coinSlug}_{coinId}";
            var path = Path.Combine(_basePath, issuerSlug, folderName);
            return path;
        }

        public string GetCoinHtmlPath(string issuerSlug, string coinSlug, long coinId)
        {
            var dir = GetCoinDirectory(issuerSlug, coinSlug, coinId);
            return Path.Combine(dir, "coin_type.html");
        }


        public FileService()
        {
            // Parameterless constructor for simple initialization if needed
        }

        public string GeneratePhpUniqId()
        {
            var now = DateTime.UtcNow;
            long seconds = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            long microseconds = (now.Ticks % 10_000_000) / 10;
            return $"{seconds:x8}{microseconds:x5}";
        }

        public void SplitImageFile(string inputPath, double splitRatio, string outPathObv, string outPathRev)
        {
            using (var fs = new FileStream(inputPath, FileMode.Open, FileAccess.Read))
            {
                var decoder = BitmapDecoder.Create(fs, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
                var frame = decoder.Frames[0];
                int width = frame.PixelWidth;
                int height = frame.PixelHeight;

                int splitX = (int)(width * splitRatio);
                
                // Crop Obverse
                var cropObv = new CroppedBitmap(frame, new System.Windows.Int32Rect(0, 0, splitX, height));
                SaveBitmap(cropObv, outPathObv);

                // Crop Reverse
                var cropRev = new CroppedBitmap(frame, new System.Windows.Int32Rect(splitX, 0, width - splitX, height));
                SaveBitmap(cropRev, outPathRev);
            }
        }

        private void SaveBitmap(BitmapSource bitmap, string path)
        {
            using (var stream = new FileStream(path, FileMode.Create))
            {
                var encoder = new JpegBitmapEncoder { QualityLevel = 95 };
                encoder.Frames.Add(BitmapFrame.Create(bitmap));
                encoder.Save(stream);
            }
        }

        public void BackupFile(string filePath, string newId)
        {
            if (!File.Exists(filePath)) return;

            string directory = Path.GetDirectoryName(filePath) ?? string.Empty;
            string fileName = Path.GetFileName(filePath);
            string backupDir = Path.Combine(directory, "bkp", newId);
            
            Directory.CreateDirectory(backupDir);
            File.Move(filePath, Path.Combine(backupDir, fileName));
        }

        public void ReplaceSplitImageInHtml(string htmlPath, string oldImageName, string newObvName, string newRevName, string titleVal)
        {
            if (!File.Exists(htmlPath)) return;

            string html = File.ReadAllText(htmlPath);
            
            // Search for the <a>...<img src="...oldImage..."...>...</a> pattern
            // Using a simple regex to capture the whole anchor block surrounding the image
            // Note: This assumes standard Numista HTML formatting
            
            string pattern = $@"<a[^>]*href=""images/{Regex.Escape(oldImageName)}""[^>]*>[\s\S]*?<img[^>]*src=""images/{Regex.Escape(oldImageName)}""[^>]*>[\s\S]*?</a>";
            
            // Replacement block (mimicking the detected Numista style)
            string replacement = $@"<a class=""coin_pic"" data-zoompic="""" data-zoompicgroup=""coin_pic"" href=""images/{newObvName}"" target=""_blank"">
<img alt=""{titleVal} - obverse"" src=""images/{newObvName}"" title=""""/>""<!--
--></a><!--
--><a class=""coin_pic"" data-zoompic="""" data-zoompicgroup=""coin_pic"" href=""images/{newRevName}"" target=""_blank""><!--
--><img alt=""{titleVal} - reverse"" src=""images/{newRevName}"" title=""""/>
</a>";

            string newHtml = Regex.Replace(html, pattern, replacement);
            
            File.WriteAllText(htmlPath, newHtml);
        }
        public bool AreFilesIdentical(string path1, string path2)
        {
            try
            {
                if (!File.Exists(path1) || !File.Exists(path2)) return false;

                using (var md5 = System.Security.Cryptography.MD5.Create())
                {
                    using (var stream1 = File.OpenRead(path1))
                    using (var stream2 = File.OpenRead(path2))
                    {
                        byte[] hash1 = md5.ComputeHash(stream1);
                        byte[] hash2 = md5.ComputeHash(stream2);
                        return System.Linq.Enumerable.SequenceEqual(hash1, hash2);
                    }
                }
            }
            catch
            {
                return false;
            }
        }

        public bool ArePixelsIdentical(string path1, string path2)
        {
            try
            {
                if (!File.Exists(path1) || !File.Exists(path2)) return false;
                
                // Use BitmapImage to decode without locking file
                var img1 = LoadBitmap(path1);
                var img2 = LoadBitmap(path2);

                if (img1.PixelWidth != img2.PixelWidth || img1.PixelHeight != img2.PixelHeight) return false;
                if (img1.Format != img2.Format) return false;

                int bytesPerPixel = (img1.Format.BitsPerPixel + 7) / 8;
                int stride = img1.PixelWidth * bytesPerPixel;
                int length = stride * img1.PixelHeight;

                byte[] data1 = new byte[length];
                byte[] data2 = new byte[length];

                img1.CopyPixels(data1, stride, 0);
                img2.CopyPixels(data2, stride, 0);

                return System.Linq.Enumerable.SequenceEqual(data1, data2);
            }
            catch
            {
                return false;
            }
        }

        public string GetFileHash(string path)
        {
             try
            {
                if (!File.Exists(path)) return string.Empty;
                using (var md5 = System.Security.Cryptography.MD5.Create())
                using (var stream = File.OpenRead(path))
                {
                    return BitConverter.ToString(md5.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
                }
            }
            catch { return string.Empty; }
        }

        public System.Windows.Media.Imaging.BitmapSource LoadBitmap(string path)
        {
            try
            {
                var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                bitmap.BeginInit();
                bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                bitmap.UriSource = new System.Uri(path);
                bitmap.EndInit();
                bitmap.Freeze(); 
                return bitmap;
            }
            catch { return null; }
        }

        public ulong CalculateDHash(string path)
        {
            try
            {
                if (!File.Exists(path)) return 0;

                // 1. Resize to 9x8 (small)
                var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                bitmap.BeginInit();
                bitmap.UriSource = new System.Uri(path);
                bitmap.DecodePixelWidth = 9; 
                bitmap.DecodePixelHeight = 8;
                bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                bitmap.EndInit();
                bitmap.Freeze();

                // 2. Convert to Greyscale (if needed, but simple avg is enough)
                // We'll read pixels directly. 9x8 is tiny.
                int width = 9;
                int height = 8;
                int stride = width * 4; // 32 bot BGRA
                byte[] pixels = new byte[height * stride];
                bitmap.CopyPixels(pixels, stride, 0);

                // 3. Compute Hash
                ulong hash = 0;
                int bitIndex = 0;

                for (int y = 0; y < 8; y++)
                {
                    for (int x = 0; x < 8; x++)
                    {
                        // Get brightness of Left (x) and Right (x+1)
                        // BGRA: B=0, G=1, R=2, A=3
                        int p1_idx = (y * stride) + (x * 4);
                        int p2_idx = (y * stride) + ((x + 1) * 4);

                        // Simple luminosity estimate: (R+R+B+G+G+G)/6 or just Avg
                        double b1 = (pixels[p1_idx] + pixels[p1_idx+1] + pixels[p1_idx+2]) / 3.0;
                        double b2 = (pixels[p2_idx] + pixels[p2_idx+1] + pixels[p2_idx+2]) / 3.0;

                        if (b1 > b2)
                        {
                            hash |= (1UL << bitIndex);
                        }
                        bitIndex++;
                    }
                }
                return hash;
            }
            catch
            {
                return 0;
            }
        }

        public (ulong leftHash, ulong rightHash) CalculateSplitHashes(string path, double splitRatio)
        {
            try
            {
                if (!File.Exists(path)) return (0, 0);

                var dim = 9; // 9x8 for dHash
                var height = 8;
                
                var original = LoadBitmap(path);
                int w = original.PixelWidth;
                int h = original.PixelHeight;
                int splitX = (int)(w * splitRatio);
                
                if (splitX < 1 || splitX >= w) return (0, 0);

                // Helper local function to compute hash from a cropped region
                ulong ComputeHashForRegion(int startX, int regionWidth)
                {
                     // Resize logic is tricky without full library support (e.g. System.Drawing is not here, checking usings)
                     // We are using WPF BitmapSource. TransformedBitmap or CroppedBitmap.
                     
                     var crop = new System.Windows.Media.Imaging.CroppedBitmap(original, new System.Windows.Int32Rect(startX, 0, regionWidth, h));
                     
                     // Now we need to resize 'crop' to 9x8.
                     // ScaleTransform + TransformedBitmap
                     double scaleX = (double)dim / regionWidth;
                     double scaleY = (double)height / h;
                     
                     var scaled = new System.Windows.Media.Imaging.TransformedBitmap(crop, new System.Windows.Media.ScaleTransform(scaleX, scaleY));
                     
                     // Convert to bytes (Gray/Read)
                     int stride = dim * 4; 
                     byte[] pixels = new byte[height * stride];
                     scaled.CopyPixels(pixels, stride, 0);
                     
                     ulong hash = 0;
                     int bitIndex = 0;
                     for (int y = 0; y < 8; y++)
                     {
                         for (int x = 0; x < 8; x++)
                         {
                             int p1 = (y * stride) + (x * 4);
                             int p2 = (y * stride) + ((x + 1) * 4);
                             
                             // Blue ch check
                             if (pixels[p1] > pixels[p2]) // Simplification: just check Blue or Avg
                                 hash |= (1UL << bitIndex);
                             bitIndex++;
                         }
                     }
                     return hash;
                }

                ulong left = ComputeHashForRegion(0, splitX);
                ulong right = ComputeHashForRegion(splitX, w - splitX);
                
                return (left, right);
            }
            catch { return (0, 0); }
        }

        public int HammingDistance(ulong hash1, ulong hash2)
        {
            ulong xor = hash1 ^ hash2;
            int dist = 0;
            while (xor > 0)
            {
                if ((xor & 1) == 1) dist++;
                xor >>= 1;
            }
            return dist;
        }

        public double DetectSplitRatio(string path)
        {
            try
            {
                if (!File.Exists(path)) return 0.5;

                var img = LoadBitmap(path);
                int width = img.PixelWidth;
                int height = img.PixelHeight;
                
                if (width < 10 || height < 10) return 0.5;

                // Lock bits manually? WPF BitmapSource copy pixels is safer.
                int stride = width * 4; 
                byte[] pixels = new byte[height * stride];
                img.CopyPixels(pixels, stride, 0);

                // Calculate "Energy" per column
                // Energy = Variance in vertical direction + Variance from average color? 
                // Simple heuristic: Sum of vertical gradients. Low vertical gradient = static column?
                // Also horizontal gradient? 
                // A gap is usually uniform color. So pixel[x,y] is roughly same as pixel[x, y+1] AND pixel[x,y] same as pixel[x+1, y].
                // Let's count "Edge Activity" in each column.
                
                long[] columnEnergy = new long[width];

                for (int x = 0; x < width; x++)
                {
                    long energy = 0;
                    for (int y = 0; y < height - 1; y++)
                    {
                        int idx = (y * stride) + (x * 4);
                        int idxDown = ((y+1) * stride) + (x * 4);
                        
                        // Blue diff
                        energy += Math.Abs(pixels[idx] - pixels[idxDown]);
                        // Green
                        energy += Math.Abs(pixels[idx+1] - pixels[idxDown+1]);
                        // Red 
                        energy += Math.Abs(pixels[idx+2] - pixels[idxDown+2]);
                    }
                    columnEnergy[x] = energy;
                }

                // Threshold for "Gap"
                // Find low energy columns.
                // Dynamic threshold? Average energy / 5?
                long avgEnergy = (long)columnEnergy.Average();
                long threshold = avgEnergy / 3; 

                // Find widest gap
                int bestGapStart = -1;
                int bestGapEnd = -1;
                int maxGapWidth = 0;

                int currentGapStart = -1;

                // Only search middle 60% of image? (Avoid borders)
                int searchStart = (int)(width * 0.2);
                int searchEnd = (int)(width * 0.8);

                for (int x = searchStart; x < searchEnd; x++)
                {
                    if (columnEnergy[x] < threshold)
                    {
                        if (currentGapStart == -1) currentGapStart = x;
                    }
                    else
                    {
                        if (currentGapStart != -1)
                        {
                            int gapWidth = x - currentGapStart;
                            if (gapWidth > maxGapWidth)
                            {
                                maxGapWidth = gapWidth;
                                bestGapStart = currentGapStart;
                                bestGapEnd = x;
                            }
                            currentGapStart = -1;
                        }
                    }
                }
                
                // Check trailing gap
                if (currentGapStart != -1)
                {
                     int gapWidth = searchEnd - currentGapStart;
                     if (gapWidth > maxGapWidth)
                     {
                         maxGapWidth = gapWidth;
                         bestGapStart = currentGapStart;
                         bestGapEnd = searchEnd;
                     }
                }

                // If found a gap, return CENTER
                if (maxGapWidth > 0 && bestGapStart != -1)
                {
                    int center = bestGapStart + (maxGapWidth / 2);
                    return (double)center / width;
                }

                return 0.5;
            }
            catch
            {
                return 0.5;
            }
        }

        public void SplitAndSaveImage(string sourcePath, double splitRatio, string outLeftPath, string outRightPath)
        {
            if (!File.Exists(sourcePath)) return;

            try 
            {
                var original = LoadBitmap(sourcePath);
                int w = original.PixelWidth;
                int h = original.PixelHeight;
                int splitX = (int)(w * splitRatio);
                
                if (splitX < 1 || splitX >= w) return; // Invalid split

                // Left (Obverse)
                var cropLeft = new CroppedBitmap(original, new Int32Rect(0, 0, splitX, h));
                SaveBitmap(cropLeft, outLeftPath);

                // Right (Reverse)
                var cropRight = new CroppedBitmap(original, new Int32Rect(splitX, 0, w - splitX, h));
                SaveBitmap(cropRight, outRightPath);
            }
            catch (Exception)
            {
                // Ignore error
            }
        }



        public void RemoveSaleTableBody(string htmlPath, string imageName)
        {
             if (!File.Exists(htmlPath)) return;
             
             try
             {
                 string html = File.ReadAllText(htmlPath);
                 string searchTarget = $"images/{imageName}"; // e.g. "images/abc.jpg"
                 int imgIndex = html.IndexOf(searchTarget, StringComparison.OrdinalIgnoreCase);
                 
                 if (imgIndex == -1) return;
                 
                 // Look for containing <tbody> backwards
                 int tbodyStart = html.LastIndexOf("<tbody", imgIndex, StringComparison.OrdinalIgnoreCase);
                 if (tbodyStart == -1) return;
                 
                 // Look for closing </tbody> forwards
                 int tbodyEnd = html.IndexOf("</tbody>", imgIndex, StringComparison.OrdinalIgnoreCase);
                 if (tbodyEnd == -1) return;
                 
                 tbodyEnd += "</tbody>".Length;
                 
                 string newHtml = html.Remove(tbodyStart, tbodyEnd - tbodyStart);
                 File.WriteAllText(htmlPath, newHtml);
             }
             catch { }
        }

        public void RemoveImageRowFromHtml(string htmlPath, string imageName)
        {
             if (!File.Exists(htmlPath)) return;
             
             try
             {
                 string html = File.ReadAllText(htmlPath);
                 string searchTarget = $"images/{imageName}";
                 int imgIndex = html.IndexOf(searchTarget, StringComparison.OrdinalIgnoreCase);
                 
                 if (imgIndex == -1) return;
                 
                 // Find opening <tr> backwards
                 int trStart = html.LastIndexOf("<tr", imgIndex, StringComparison.OrdinalIgnoreCase);
                 if (trStart == -1) return;
                 
                 // Find closing </tr> forwards
                 int trEnd = html.IndexOf("</tr>", imgIndex, StringComparison.OrdinalIgnoreCase);
                 if (trEnd == -1) return;
                 
                 // Include the closing tag
                 trEnd += "</tr>".Length;
                 
                 string newHtml = html.Remove(trStart, trEnd - trStart);
                 File.WriteAllText(htmlPath, newHtml);
             }
             catch { }
        }

        public void ReplaceImageReferenceInHtml(string htmlPath, string oldImageName, string newImageName)
        {
            if (!File.Exists(htmlPath)) return;
            string html = File.ReadAllText(htmlPath);

            // Simple string replacement for filename in SRC and HREF tags
            // Use regex for safety to avoid partial matches
            
            // Matches: images/filename.jpg, images\filename.jpg
            // We want to replace just the filename part.
            
            string pattern = Regex.Escape(oldImageName);
            string replacement = newImageName;
            
            // Just replace the filename occurrence if it's prefixed by / or \ or " or '
            // Actually, in Numista HTML it's usually href="images/..." or src="images/..."
            
            string newHtml = Regex.Replace(html, pattern, replacement, RegexOptions.IgnoreCase);
            
            if (newHtml != html)
            {
                File.WriteAllText(htmlPath, newHtml);
            }
        }

        public void UpdateImageReferenceInHtml(string htmlPath, string oldImage, string newImage)
        {
             // This can just reuse ReplaceImageReferenceInHtml (renaming it for clarity or alias)
             ReplaceImageReferenceInHtml(htmlPath, oldImage, newImage);
        }
        
        public void MoveToBackup(string filePath)
        {
            if (!File.Exists(filePath)) return;
            
            try
            {
                string dir = Path.GetDirectoryName(filePath);
                string bkpDir = Path.Combine(dir, "bkp");
                if (!Directory.Exists(bkpDir)) Directory.CreateDirectory(bkpDir);
                
                string fileName = Path.GetFileName(filePath);
                string dest = Path.Combine(bkpDir, fileName);
                
                // Overwrite if exists in backup
                if (File.Exists(dest)) File.Delete(dest);
                
                File.Move(filePath, dest);
            }
            catch { }
        }


        public void SwapFullImageReferencesInHtml(string htmlPath, string image1, string image2)
        {
            if (!File.Exists(htmlPath)) return;

            try
            {
                string content = File.ReadAllText(htmlPath);
                
                string token = "___SWAP_TOKEN___";
                // Simple 3-sided swap
                content = content.Replace(image1, token);
                content = content.Replace(image2, image1);
                content = content.Replace(token, image2);
                
                File.WriteAllText(htmlPath, content);
            }
            catch { }
        }

        public System.Threading.Tasks.Task BackupCoinHtmlAsync(string issuerSlug, string coinFolder)
        {
             return System.Threading.Tasks.Task.Run(() => 
             {
                 try 
                 {
                     string path = Path.Combine(_basePath, issuerSlug, coinFolder, "coin_type.html");
                     if (!File.Exists(path)) return;
                     
                     string bkpDir = Path.Combine(_basePath, issuerSlug, coinFolder, "bkp");
                     if (!Directory.Exists(bkpDir)) Directory.CreateDirectory(bkpDir);
                     
                     string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                     string dest = Path.Combine(bkpDir, $"coin_type_{timestamp}.html");
                     
                     File.Copy(path, dest, true);
                 }
                 catch { }
             });
        }
    }
}
