using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Mintada.Navigator.Models;
using Mintada.Navigator.Services;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using IO = System.IO;
using System.Collections.Generic;
using System.Threading;

using System.Text.Json;
using Mintada.Navigator.Views;

namespace Mintada.Navigator.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        private readonly DatabaseService _databaseService;
        private readonly FileService _fileService;
        private readonly Services.AnalysisService _analysisService;
        private readonly Services.ImageAnalysisService _imageAnalysisService;
        private readonly CoinParserService _coinParserService;

        [ObservableProperty]
        private ParsedCoinData? _parsedData;
        
        private List<Issuer> _allIssuers = new();
        private List<Issuer> _rootIssuers = new(); 
        private long? _pendingCoinSelectionId = null;
        private long? _exclusiveCoinId = null;
        private Task? _activeFilteringTask;
        private bool _suppressFilterChanges = false;
        private readonly string _cacheFilePath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "issuers_cache.json");
        private readonly string _settingsFilePath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "settings.json");
        private CancellationTokenSource? _swapCts;        
        public IRelayCommand LoadIssuersCommand { get; }



        [ObservableProperty]
        private bool _isNonReferenceFilterActive;

        [ObservableProperty]
        private ObservableCollection<Issuer> _issuers = new();

        [ObservableProperty]
        private Issuer? _selectedIssuer;

        [ObservableProperty]
        private ObservableCollection<CoinType> _coins = new();

        [ObservableProperty]
        [NotifyCanExecuteChangedFor(nameof(OpenCoinFolderCommand))]
        [NotifyCanExecuteChangedFor(nameof(ImportFromUcoinCommand))]
        private CoinType? _selectedCoin;

        [ObservableProperty]
        private Uri? _htmlSource;

        [ObservableProperty]
        private string _filterText = string.Empty;

        [ObservableProperty]
        private string _searchCoinIdText = string.Empty;

        partial void OnSearchCoinIdTextChanged(string value)
        {
            if (string.IsNullOrWhiteSpace(value) && _exclusiveCoinId.HasValue)
            {
                // User cleared the search box. Reset exclusive mode and reload all coins for current issuer.
                _exclusiveCoinId = null;
                if (SelectedIssuer != null)
                {
                    _ = LoadCoinsForIssuer(SelectedIssuer);
                }
            }
        }

        [ObservableProperty]
        private string _statusMessage = "Ready.";

        [ObservableProperty]
        private bool _isHideFixedFilterActive;

        [ObservableProperty]
        private bool _isShowCompletedFilterActive;

        [ObservableProperty]
        private bool _isTransferModeActive;

        [ObservableProperty]
        private CoinType? _transferTargetCoin;

        [ObservableProperty]
        [NotifyCanExecuteChangedFor(nameof(SplitSampleCommand))]
        [NotifyCanExecuteChangedFor(nameof(SwapSampleCommand))]
        [NotifyCanExecuteChangedFor(nameof(ChooseBestSampleCommand))]
        [NotifyCanExecuteChangedFor(nameof(PromoteSampleCommand))]
        [NotifyCanExecuteChangedFor(nameof(TransferSampleCommand))]
        [NotifyCanExecuteChangedFor(nameof(MarkAsSampleCommand))]
        private CoinSample? _selectedSample;

        [ObservableProperty]
        private int _selectedTabIndex = 0;

        [ObservableProperty]
        private ObservableCollection<RulerPeriodGroup> _rulers = new();

        [ObservableProperty]
        private ObservableCollection<LeafIssuerViewModel> _leafIssuers = new();
        
        private List<LeafIssuerViewModel> _allLeafIssuers = new();


        public ObservableCollection<CoinSample> SelectedSamples { get; } = new();

        public MainViewModel()
        {
            // Hardcoded paths for now - in a real app these would be configured
            string rootPath = @"D:\projects\mintada\scrappers\numista\coin_types\html";
            string dbPath = @"D:\projects\mintada\data\numista\coins.db";
            string pythonPath = @"d:\projects\mintada\.venv\Scripts\python.exe"; 
            string scriptPath = @"d:\projects\mintada\tools\segmentation\detect_swap_interactive.py";

            _fileService = new FileService(rootPath);
            _databaseService = new DatabaseService(dbPath);
            _analysisService = new Services.AnalysisService(pythonPath, scriptPath);
            _imageAnalysisService = new Services.ImageAnalysisService();
            _coinParserService = new CoinParserService();

            LoadIssuersCommand = new RelayCommand(async () => await LoadData(false));
            
             // Start analysis service in background
             Task.Run(async () => await _analysisService.StartAsync());


            // Load Settings
            LoadSettings();

            // Load data on startup (try cache first)
            _ = LoadData(forceRefresh: false);
        }

        private void LoadSettings()
        {
            try
            {
                if (IO.File.Exists(_settingsFilePath))
                {
                    string json = IO.File.ReadAllText(_settingsFilePath);
                    var settings = JsonSerializer.Deserialize<Dictionary<string, bool>>(json);
                    if (settings != null)
                    {
                        if (settings.ContainsKey("IsNonReferenceFilterActive"))
                            IsNonReferenceFilterActive = settings["IsNonReferenceFilterActive"];
                        if (settings.ContainsKey("IsHideFixedFilterActive"))
                            IsHideFixedFilterActive = settings["IsHideFixedFilterActive"];
                        if (settings.ContainsKey("IsShowCompletedFilterActive"))
                            IsShowCompletedFilterActive = settings["IsShowCompletedFilterActive"];
                    }
                }
            }
            catch { /* Ignore settings load error */ }
        }

        private void SaveSettings()
        {
            try
            {
                var settings = new Dictionary<string, bool>
                {
                    { "IsNonReferenceFilterActive", IsNonReferenceFilterActive },
                    { "IsHideFixedFilterActive", IsHideFixedFilterActive },
                    { "IsShowCompletedFilterActive", IsShowCompletedFilterActive }
                };
                string json = JsonSerializer.Serialize(settings);
                IO.File.WriteAllText(_settingsFilePath, json);
            }
            catch { /* Ignore settings save error */ }
        }


        [RelayCommand]
        private async Task Refresh()
        {
            await LoadData(forceRefresh: true);
        }

        private async Task LoadData(bool forceRefresh)
        {
            try
            {
                bool loadedFromCache = false;
                if (!forceRefresh && IO.File.Exists(_cacheFilePath))
                {
                    try
                    {
                        StatusMessage = "Loading cache...";
                        string json = await IO.File.ReadAllTextAsync(_cacheFilePath);
                        var cached = JsonSerializer.Deserialize<List<Issuer>>(json);
                        if (cached != null)
                        {
                            _allIssuers = cached;
                            loadedFromCache = true;
                            StatusMessage = "Loaded from cache.";
                        }
                    }
                    catch 
                    {
                        // Cache invalid/corrupt, ignore
                    }
                }

                if (!loadedFromCache)
                {
                    StatusMessage = "Fetching data from DB...";
                    var issuers = await _databaseService.GetIssuersAsync();
                    var interestingIssuerIds = await _databaseService.GetIssuersWithNonReferenceSamplesAsync();
                    
                    foreach(var issuer in issuers)
                    {
                        issuer.HasNonReferenceSamples = interestingIssuerIds.Contains(issuer.Id);
                    }

                    _allIssuers = issuers;

                    // Save cache
                    try
                    {
                        string json = JsonSerializer.Serialize(_allIssuers);
                        await IO.File.WriteAllTextAsync(_cacheFilePath, json);
                    }
                    catch { /* Ignore save error */ }
                }

                BuildHierarchy();
                await BuildLeafIssuers();
                await FilterIssuers();
                StatusMessage = "Ready.";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error loading data: {ex.Message}";
            }
        }

        partial void OnFilterTextChanged(string value)
        {
            if (_suppressFilterChanges) return;
            _activeFilteringTask = FilterIssuers();
        }

        partial void OnIsNonReferenceFilterActiveChanged(bool value)
        {
            if (_suppressFilterChanges) return;
            _activeFilteringTask = FilterIssuers();
            SaveSettings();
            if (SelectedIssuer != null)
            {
                _ = LoadCoinsForIssuer(SelectedIssuer, SelectedCoin?.Id);
            }
        }

        partial void OnIsHideFixedFilterActiveChanged(bool value)
        {
            if (_suppressFilterChanges) return;
            if (value && IsShowCompletedFilterActive) IsShowCompletedFilterActive = false;
            _activeFilteringTask = FilterIssuers();
            SaveSettings();
            if (SelectedIssuer != null) _ = LoadCoinsForIssuer(SelectedIssuer, SelectedCoin?.Id);
        }

        partial void OnIsShowCompletedFilterActiveChanged(bool value)
        {
            if (_suppressFilterChanges) return;
            if (value && IsHideFixedFilterActive) IsHideFixedFilterActive = false;
            _activeFilteringTask = FilterIssuers();
            SaveSettings();
            if (SelectedIssuer != null) _ = LoadCoinsForIssuer(SelectedIssuer, SelectedCoin?.Id);
        }

        partial void OnSelectedIssuerChanged(Issuer? value)
        {
            if (value != null)
            {
                StatusMessage = $"Selected Issuer: {value.Name} ({value.UrlSlug})";
                
                if (SelectedTabIndex == 0) // Coin Types tab
                {
                     long? pendingId = _pendingCoinSelectionId;
                     _pendingCoinSelectionId = null; // Clear it immediately

                    _ = LoadCoinsForIssuer(value, pendingId);
                }
                else // Rulers tab
                {
                    _ = AutoAssociateAndLoadRulers(value);
                }
            }
            else 
            {
                StatusMessage = "Selection Cleared.";
                Coins.Clear();
                Rulers.Clear();
            }
        }

        partial void OnSelectedTabIndexChanged(int value)
        {
            if (value == 1) // Rulers tab
            {
                // Clear coins when switching to rulers tab
                Coins.Clear();
                
                // Load Numista rulers page in right panel
                HtmlSource = new Uri("https://en.numista.com/catalogue/rulers.php");
                
                // Load rulers for selected issuer if any
                if (SelectedIssuer != null)
                {
                    _ = AutoAssociateAndLoadRulers(SelectedIssuer);
                }
            }
            else // Coin Types tab
            {
                // Clear rulers when switching to coin types tab
                Rulers.Clear();
                
                // Clear HTML source when leaving rulers tab
                HtmlSource = null;
                
                // Reload coins for selected issuer if any
                if (SelectedIssuer != null)
                {
                    _ = LoadCoinsForIssuer(SelectedIssuer);
                }
            }
        }

        private CoinType? _originalCoinBeforeTransfer;

        partial void OnSelectedCoinChanged(CoinType? value)
        {
            // Debug output
            System.Diagnostics.Debug.WriteLine($"OnSelectedCoinChanged: IsTransferModeActive={IsTransferModeActive}, value={value?.Title ?? "null"}");
            
            // If in transfer mode, set the clicked coin as the transfer target
            if (IsTransferModeActive && value != null)
            {
                // Don't process if we're reverting back to the original coin
                if (value == _originalCoinBeforeTransfer)
                {
                    System.Diagnostics.Debug.WriteLine("  Skipping - this is the original coin being restored");
                    return;
                }
                
                TransferTargetCoin = value;
                StatusMessage = $"Target selected: {value.Title} | Subtitle: {value.Subtitle} | Samples: {value.Samples?.Count ?? 0}";
                System.Diagnostics.Debug.WriteLine($"TransferTargetCoin set to: {value.Title}");
                System.Diagnostics.Debug.WriteLine($"  Title: '{value.Title}'");
                System.Diagnostics.Debug.WriteLine($"  Subtitle: '{value.Subtitle}'");
                System.Diagnostics.Debug.WriteLine($"  Samples count: {value.Samples?.Count ?? 0}");
                
                // Use Dispatcher to revert selection after UI updates
                System.Windows.Application.Current.Dispatcher.InvokeAsync(() =>
                {
                    SelectedCoin = _originalCoinBeforeTransfer;
                }, System.Windows.Threading.DispatcherPriority.Background);
                
                return; // Don't load the coin normally
            }

            if (value != null && SelectedIssuer != null)
            {
                string path = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, value.CoinTypeSlug, value.Id);
                if (IO.File.Exists(path))
                {
                    HtmlSource = new Uri(path);

                    // Parse Data
                    try
                    {
                        var content = IO.File.ReadAllText(path);
                        var data = _coinParserService.Parse(content);
                        ParsedData = data;
                        
                        // Fire and forget verification
                        _ = Task.Run(async () => 
                        {
                            try 
                            {
                                // Verify Ruler
                                if (ParsedData.RulerId.HasValue && ParsedData.RulerId.Value != 0 && SelectedIssuer != null)
                                {
                                    var info = await _databaseService.GetRulerInfoAsync(SelectedIssuer.Id, ParsedData.RulerId.Value);
                                    if (info != null)
                                    {
                                        ParsedData.DbRulerName = info.Value.Name;
                                        ParsedData.DbRulerYears = info.Value.YearsText;
                                        ParsedData.IsRulerVerified = true;
                                        ParsedData.NeedsInspection = false;
                                    }
                                    else
                                    {
                                        ParsedData.NeedsInspection = true;
                                        ParsedData.IsRulerVerified = false;
                                    }
                                }

                                // Verify Shape
                                int? verifiedShapeId = null;
                                if (value.ShapeId.HasValue)
                                {
                                    verifiedShapeId = value.ShapeId.Value;
                                }
                                else if (!string.IsNullOrWhiteSpace(ParsedData.Shape))
                                {
                                    var shapeId = await _databaseService.GetShapeIdByNameAsync(ParsedData.Shape);
                                    if (shapeId.HasValue)
                                    {
                                        verifiedShapeId = shapeId.Value;
                                    }
                                }

                                if (verifiedShapeId.HasValue)
                                {
                                    ParsedData.DbShapeId = verifiedShapeId;
                                    System.Windows.Application.Current.Dispatcher.Invoke(() => OnPropertyChanged(nameof(ParsedData)));
                                }

                                
                                OnPropertyChanged(nameof(ParsedData));
                            }
                            catch (Exception ex)
                            {
                                System.Diagnostics.Debug.WriteLine($"Error verifying data: {ex.Message}");
                            }
                        });
                    }
                    catch (Exception ex)
                    {
                         System.Diagnostics.Debug.WriteLine($"Error parsing coin data: {ex.Message}");
                         StatusMessage = $"PARSING ERROR: {ex.Message}";
                         ParsedData = null;
                         System.Windows.MessageBox.Show($"Error parsing coin HTML: {ex.Message}", "Parsing Error", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                    }
                }
                else
                {
                    HtmlSource = null;
                }
                
                // Trigger Swap Analysis
                CheckForSwappedFaces(value);
            }
            else
            {
                HtmlSource = null;
            }
        }

        private void CheckForSwappedFaces(CoinType coin)
        {
             _swapCts?.Cancel();
             _swapCts = new CancellationTokenSource();
             var token = _swapCts.Token;

             Task.Run(async () => 
             {
                 if (token.IsCancellationRequested) return;

                 var reference = coin.Samples.FirstOrDefault(s => s.SampleType == 1);
                 if (reference == null || !reference.HasObverse || !reference.HasReverse) return;
                 
                 string refObv = reference.ObversePath;
                 string refRev = reference.ReversePath;
                 if (string.IsNullOrEmpty(refObv) || string.IsNullOrEmpty(refRev)) return;

                 var samplesToCheck = coin.Samples.Where(s => s.SampleType != 1 && !s.IsCombinedImage && s.HasObverse && s.HasReverse).ToList();
                 
                 var tasks = samplesToCheck.Select(async sample => 
                 {
                     if (token.IsCancellationRequested) return;
                     
                     try
                     {
                         bool isFlip = await _analysisService.CheckFlipAsync(refObv, refRev, sample.ObversePath, sample.ReversePath, token);
                     
                         if (token.IsCancellationRequested) return;

                         System.Windows.Application.Current.Dispatcher.Invoke(() => 
                         {
                             if (coin == SelectedCoin && !token.IsCancellationRequested) 
                             {
                                 sample.IsSwapSuggested = isFlip;
                             }
                         });
                     }
                     catch (OperationCanceledException) { }
                     catch (Exception) { }
                 });

                 await Task.WhenAll(tasks);
             }, token);
        }

        [RelayCommand]
        private void OpenCoinFolder(CoinType coin)
        {
            if (coin != null && SelectedIssuer != null)
            {
                string path = _fileService.GetCoinDirectory(SelectedIssuer.UrlSlug, coin.CoinTypeSlug, coin.Id);
                if (IO.Directory.Exists(path))
                {
                    System.Diagnostics.Process.Start("explorer.exe", path);
                }
            }
        }

        [RelayCommand]
        private async Task ToggleFixed(CoinType coin)
        {
            if (coin == null) return;
            coin.IsFixed = !coin.IsFixed;
            await _databaseService.UpdateCoinFixedStatusAsync(coin.Id, coin.IsFixed);
        }


        
        partial void OnSelectedSampleChanged(CoinSample? value)
        {
             SplitSampleCommand.NotifyCanExecuteChanged();
             if (value != null && value.IsCombinedImage)
             {
                 // Calculate split line if not already done (or always recalc?)
                 // Do it async to not block UI
                 Task.Run(() => 
                 {
                     var ratio = _fileService.DetectSplitRatio(value.ObversePath);
                     // Update on UI thread
                     System.Windows.Application.Current.Dispatcher.Invoke(() => 
                     {
                         if(value == SelectedSample) // check if still selected
                            value.SplitRatio = ratio;
                     });
                 });
             }
        }

        [RelayCommand(CanExecute = nameof(CanSplitSample))]
        private async Task SplitSample()
        {
            if (SelectedCoin == null || SelectedIssuer == null || !SelectedSamples.Any()) return;
            
            // Snapshot list
            var samplesToProcess = SelectedSamples.ToList();

            foreach(var sample in samplesToProcess)
            {
                if (!sample.IsCombinedImage) continue;

                var ratio = sample.SplitRatio;
                
                // Paths
                var dir = _fileService.GetCoinDirectory(SelectedIssuer.UrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                var imagesDir = System.IO.Path.Combine(dir, "images");
                
                // 1. Generate two unique names (Simulate PHP uniqid)
                string ext = System.IO.Path.GetExtension(sample.ObversePath);
                
                string id1 = _fileService.GeneratePhpUniqId();
                await Task.Delay(15); // Ensure time tick change for uniqueness
                string id2 = _fileService.GeneratePhpUniqId();
                
                // Safety check
                while (id1 == id2)
                {
                    await Task.Delay(10);
                    id2 = _fileService.GeneratePhpUniqId();
                }
    
                string newObvName = $"{id1}{ext}";
                string newRevName = $"{id2}{ext}";
                
                string newObvPath = System.IO.Path.Combine(imagesDir, newObvName);
                string newRevPath = System.IO.Path.Combine(imagesDir, newRevName);
                
                try
                {
                    // 2. Perform Physical Split
                    _fileService.SplitAndSaveImage(sample.ObversePath, ratio, newObvPath, newRevPath);
                    
                    // 3. Update Database
                    string oldImageName = sample.ObverseImage ?? System.IO.Path.GetFileName(sample.ObversePath);
                    
                    await _databaseService.UpdateCoinSampleImagesAsync(SelectedCoin.Id, oldImageName, newObvName, newRevName);
                    
                    // 4. Update HTML
                    string htmlPath = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                    _fileService.ReplaceSplitImageInHtml(htmlPath, oldImageName, newObvName, newRevName, SelectedCoin.Title);
                    
                    // 5. Backup Original
                    _fileService.BackupFile(sample.ObversePath, newObvName);
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Error parsing coin data: {ex.Message}");
                    StatusMessage = $"PARSING ERROR: {ex.Message}";
                    // Assuming ParsedData is a property of this ViewModel
                    // ParsedData = null; 
                    
                    // Show visible alert
                    System.Windows.MessageBox.Show($"Error parsing coin HTML: {ex.Message}", "Parsing Error", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                }
            }
            
            // 6. Reload once after all processed
            await LoadCoinsForIssuer(SelectedIssuer, SelectedCoin.Id);
        }

        private bool CanSplitSample()
        {
            return SelectedSamples.Any() && SelectedSamples.All(s => s.IsCombinedImage);
        }

        [RelayCommand]
        private void ViewFullImage(string path)
        {
            if (string.IsNullOrEmpty(path) || !IO.File.Exists(path)) return;
            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(path) { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error opening image: {ex.Message}";
            }
        }

        [RelayCommand(CanExecute = nameof(CanPromoteSample))]
        private async Task PromoteSample()
        {
            if (SelectedCoin == null || SelectedSample == null) return;
            
            var coin = SelectedCoin;
            var promoted = SelectedSample;

            if (promoted.SampleType == 1) return;

            var demoted = coin.Samples.FirstOrDefault(s => s.SampleType == 1);
            
            try 
            {
                // 1. Backup
                // Determine absolute path for HTML
                 string coinFolder = $"{coin.CoinTypeSlug}_{coin.Id}";
                 
                 // _fileService.BackupCoinHtmlAsync uses this folder name relative to its base path.
                 await _fileService.BackupCoinHtmlAsync(coin.IssuerUrlSlug, coinFolder);

                 // 2. Update DB
                 // Promote
                 await _databaseService.UpdateCoinSampleTypeAsync(coin.Id, promoted.ObverseImage, 1);
                 
                 // Demote (if exists) -> Type 2
                 if (demoted != null)
                 {
                     await _databaseService.UpdateCoinSampleTypeAsync(coin.Id, demoted.ObverseImage, 2);
                 }

                 // 3. Update HTML
                 string htmlPath = _fileService.GetCoinHtmlPath(coin.IssuerUrlSlug, coin.CoinTypeSlug, coin.Id);
                 if (IO.File.Exists(htmlPath))
                 {
                     var doc = new HtmlAgilityPack.HtmlDocument();
                     doc.Load(htmlPath);

                     // 3a. Update Main Image (fiche_photo)
                     var fichePhoto = doc.GetElementbyId("fiche_photo");
                     if (fichePhoto != null)
                     {
                         // Usually 2 links (obv, rev)
                         var links = fichePhoto.Descendants("a").ToList();
                         if (links.Count >= 1)
                         {
                             links[0].SetAttributeValue("href", $"images/{promoted.ObverseImage}");
                             var img = links[0].Descendants("img").FirstOrDefault();
                             if (img != null) img.SetAttributeValue("src", $"images/{promoted.ObverseImage}");
                         }
                         if (links.Count >= 2 && !string.IsNullOrEmpty(promoted.ReverseImage))
                         {
                             links[1].SetAttributeValue("href", $"images/{promoted.ReverseImage}");
                             var img = links[1].Descendants("img").FirstOrDefault();
                             if (img != null) img.SetAttributeValue("src", $"images/{promoted.ReverseImage}");
                         }
                     }

                     // 3b. Handle Demoted
                     if (demoted != null)
                     {
                         var examplesHeader = doc.DocumentNode.Descendants("h3").FirstOrDefault(h => h.InnerText.Contains("Examples of the type"));
                         HtmlAgilityPack.HtmlNode examplesDiv = null;

                         if (examplesHeader != null)
                         {
                             // Scenario 2: Exists
                             var section = examplesHeader.ParentNode;
                             examplesDiv = section.Descendants("div").FirstOrDefault(d => d.Id == "examples_list");
                         }
                         else
                         {
                             // Scenario 1: Create
                             var pastSales = doc.DocumentNode.Descendants("section").FirstOrDefault(s => s.Descendants("h3").Any(h => h.InnerText.Contains("Past sales")));
                             
                             var newSection = HtmlAgilityPack.HtmlNode.CreateNode(
                                 "<section><h3>Examples of the type</h3><div id=\"examples_list\"></div></section>");

                             if (pastSales != null)
                             {
                                 pastSales.ParentNode.InsertBefore(newSection, pastSales);
                             }
                             else
                             {
                                 // Append to main content? Usually 'fiche_content' or similar. 
                                 // Fallback: append after fiche_descriptions
                                 var descriptions = doc.GetElementbyId("fiche_descriptions");
                                 if (descriptions != null)
                                     descriptions.ParentNode.InsertAfter(newSection, descriptions);
                             }
                             examplesDiv = newSection.Descendants("div").FirstOrDefault(d => d.Id == "examples_list");
                         }

                         if (examplesDiv != null)
                         {
                             // If Promoted was Type 2, it might be in this list.
                             // Strategy: Iterate list. If we find Promoted, replace with Demoted.
                             // If we don't find Promoted (was Type 3), Append Demoted.

                             bool replaced = false;
                             var exampleImages = examplesDiv.Descendants("div").Where(d => d.HasClass("example_image")).ToList();

                             foreach (var div in exampleImages)
                             {
                                 var links = div.Descendants("a").ToList();
                                 var obvLink = links.FirstOrDefault();
                                 
                                 // Check if first link matches promoted obverse
                                 if (obvLink != null && obvLink.GetAttributeValue("href", "").Contains(promoted.ObverseImage))
                                 {
                                     // Replace Obverse
                                     obvLink.SetAttributeValue("href", $"images/{demoted.ObverseImage}");
                                     var img = obvLink.Descendants("img").FirstOrDefault();
                                     if (img != null) img.SetAttributeValue("src", $"images/{demoted.ObverseImage}");
                                     
                                     // Handle Reverse
                                     if (!string.IsNullOrEmpty(demoted.ReverseImage))
                                     {
                                         if (links.Count > 1)
                                         {
                                             // Replace existing reverse
                                             links[1].SetAttributeValue("href", $"images/{demoted.ReverseImage}");
                                             var imgRev = links[1].Descendants("img").FirstOrDefault();
                                             if (imgRev != null) imgRev.SetAttributeValue("src", $"images/{demoted.ReverseImage}");
                                         }
                                         else
                                         {
                                             // Append reverse if missing (unlikely but possible)
                                             var revHtml = $@"<!--
--><a href=""images/{demoted.ReverseImage}""><img src=""images/{demoted.ReverseImage}""></a>";
                                             var revNode = HtmlAgilityPack.HtmlNode.CreateNode(revHtml);
                                             div.AppendChild(revNode);
                                         }
                                     }
                                     
                                     replaced = true;
                                     break; // Assume only one occurrence
                                 }
                             }

                             if (!replaced)
                             {
                                 // Append new
                                 var outerDiv = HtmlAgilityPack.HtmlNode.CreateNode("<div></div>");
                                 var innerDiv = HtmlAgilityPack.HtmlNode.CreateNode("<div class=\"example_image\"></div>");
                                 
                                 // Link 1
                                 var link1 = HtmlAgilityPack.HtmlNode.CreateNode($"<a href=\"images/{demoted.ObverseImage}\"><img src=\"images/{demoted.ObverseImage}\"></a>");
                                 innerDiv.AppendChild(link1);

                                 if (!string.IsNullOrEmpty(demoted.ReverseImage))
                                 {
                                     // Comment for spacing
                                     // innerDiv.AppendChild(HtmlAgilityPack.HtmlNode.CreateNode("<!-- -->"));
                                     // Actually, let's just append the second link. 
                                     // If we really need the comment for layout (to kill whitespace), we can try text node?
                                     // But mostly it's fine. Or adding the comment node explicitly.
                                     
                                     var link2 = HtmlAgilityPack.HtmlNode.CreateNode($"<a href=\"images/{demoted.ReverseImage}\"><img src=\"images/{demoted.ReverseImage}\"></a>");
                                      innerDiv.AppendChild(link2);
                                 }

                                 outerDiv.AppendChild(innerDiv);
                                 examplesDiv.AppendChild(outerDiv);
                             }
                         }
                     }

                     doc.Save(htmlPath);
                 }

                 // 4. Reload
                 await LoadCoinsForIssuer(SelectedIssuer, coin.Id);
                 StatusMessage = "Promoted sample successfully.";
            }
            catch (Exception ex)
            {
               StatusMessage = $"Error promoting sample: {ex.Message}";
            }
        }

        private bool CanDeleteSample()
        {
            // Only allow deleting a SINGLE sample that is Type 3 (Past Sales)
            // AND there must be at least one other Type 3 sample (don't delete the last one)
            return SelectedSamples != null && 
                   SelectedSamples.Count == 1 && 
                   SelectedSamples[0].SampleType == 3 &&
                   SelectedCoin != null &&
                   SelectedCoin.Samples.Count(s => s.SampleType == 3) > 1;
        }

        [RelayCommand(CanExecute = nameof(CanDeleteSample))]
        private async Task DeleteSample()
        {
             if (SelectedCoin == null || !CanDeleteSample()) return;

             var result = System.Windows.MessageBox.Show(
                 "Are you sure you want to delete this sample?", 
                 "Confirm Delete", 
                 System.Windows.MessageBoxButton.YesNo, 
                 System.Windows.MessageBoxImage.Question);

             if (result != System.Windows.MessageBoxResult.Yes) return;

             var sample = SelectedSamples[0];
             var coin = SelectedCoin; // Snapshot coin
             string obvName = sample.ObverseImage ?? System.IO.Path.GetFileName(sample.ObversePath);

             try
             {
                 StatusMessage = "Deleting sample...";
                 
                 // 1. Soft Delete in DB
                 await _databaseService.SoftDeleteCoinSampleAsync(coin.Id, obvName);

                 // 2. Remove from HTML
                 // Use RemoveSaleTableBody to ensure clean removal of <tbody>
                 string htmlPath = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, coin.CoinTypeSlug, coin.Id);
                 if (!string.IsNullOrEmpty(obvName))
                 {
                     _fileService.RemoveSaleTableBody(htmlPath, obvName);
                 }
                 
                 // 3. Reload
                 // Preserve selection if possible, but the deleted one is gone.
                 // Passing null or coin.Id should work (it might just gracefully handle missing).
                 await LoadCoinsForIssuer(SelectedIssuer, coin.Id);
                 StatusMessage = "Sample deleted.";
             }
             catch(Exception ex)
             {
                 StatusMessage = $"Error deleting sample: {ex.Message}";
             }
        }

        private bool CanTransferSample()
        {
            // Only allow transferring a SINGLE sample that is NOT Type 1 (reference)
            return SelectedSamples != null && 
                   SelectedSamples.Count == 1 && 
                   SelectedSamples[0].SampleType != 1;
        }

        [RelayCommand(CanExecute = nameof(CanTransferSample))]
        private void TransferSample()
        {
            if (!CanTransferSample()) return;
            
            // Store the original coin to preserve bottom panel
            _originalCoinBeforeTransfer = SelectedCoin;
            
            // Enter transfer mode and open dialog window
            IsTransferModeActive = true;
            TransferTargetCoin = null;
            StatusMessage = "Select target coin type from the list...";
            
            // Open the transfer dialog window (non-modal)
            var dialog = new Views.TransferDialog();
            dialog.SetViewModel(this);
            dialog.Owner = System.Windows.Application.Current.MainWindow;
            dialog.Topmost = true; // Keep on top
            dialog.Show(); // Non-modal - allows interaction with main window
        }

        [RelayCommand]
        private void CancelTransfer()
        {
            IsTransferModeActive = false;
            TransferTargetCoin = null;
            StatusMessage = "Transfer cancelled.";
        }

        [RelayCommand]
        private async Task ConfirmTransfer()
        {
            if (TransferTargetCoin == null || SelectedSamples == null || SelectedSamples.Count != 1)
            {
                StatusMessage = "No target coin selected.";
                return;
            }

            var sample = SelectedSamples[0];
            var sourceCoin = SelectedCoin;
            var targetCoin = TransferTargetCoin;

            if (sourceCoin == null || SelectedIssuer == null)
            {
                StatusMessage = "Source coin not found.";
                return;
            }

            try
            {
                StatusMessage = $"Transferring sample to {targetCoin.Title}...";

                // 1. Update database: change coin_type_id and set sample_type to 2
                await _databaseService.TransferSampleToCoinTypeAsync(
                    sourceCoin.Id,
                    sample.ObverseImage,
                    targetCoin.Id
                );

                // 2. Move image files from source to target folder
                var sourceDir = _fileService.GetCoinDirectory(SelectedIssuer.UrlSlug, sourceCoin.CoinTypeSlug, sourceCoin.Id);
                var targetDir = _fileService.GetCoinDirectory(SelectedIssuer.UrlSlug, targetCoin.CoinTypeSlug, targetCoin.Id);

                // Move obverse image
                var sourceObverse = IO.Path.Combine(sourceDir, "images", sample.ObverseImage);
                var targetObverse = IO.Path.Combine(targetDir, "images", sample.ObverseImage);
                if (IO.File.Exists(sourceObverse))
                {
                    IO.Directory.CreateDirectory(IO.Path.GetDirectoryName(targetObverse)!);
                    IO.File.Move(sourceObverse, targetObverse, overwrite: true);
                }

                // Move reverse image if it exists
                if (!string.IsNullOrEmpty(sample.ReverseImage))
                {
                    var sourceReverse = IO.Path.Combine(sourceDir, "images", sample.ReverseImage);
                    var targetReverse = IO.Path.Combine(targetDir, "images", sample.ReverseImage);
                    if (IO.File.Exists(sourceReverse))
                    {
                        IO.File.Move(sourceReverse, targetReverse, overwrite: true);
                    }
                }

                StatusMessage = $"Sample transferred successfully to {targetCoin.Title}";

                // 3. Reload the source coin to reflect the removed sample
                await LoadCoinsForIssuer(SelectedIssuer, sourceCoin.Id);
            }
            catch (Exception ex)
            {
                StatusMessage = $"Transfer failed: {ex.Message}";
                System.Diagnostics.Debug.WriteLine($"Transfer error: {ex}");
            }
            
            // Exit transfer mode
            IsTransferModeActive = false;
            TransferTargetCoin = null;

            await Task.CompletedTask;
        }

        private bool CanMarkAsSample()
        {
            return SelectedCoin != null && SelectedSamples.Count >= 1;
        }

        [RelayCommand(CanExecute = nameof(CanMarkAsSample))]
        private void MarkAsSample()
        {
            if (!CanMarkAsSample()) return;
            
            // Open the Mark As dialog window with all selected samples
            var dialog = new Views.MarkAsDialog();
            dialog.SetViewModel(this, SelectedSamples.ToList());
            dialog.Owner = System.Windows.Application.Current.MainWindow;
            dialog.ShowDialog();
        }

        [RelayCommand]
        public async Task SaveSampleMarkings(CoinSample sample)
        {
            if (SelectedCoin == null || SelectedIssuer == null) return;
            
            try
            {
                StatusMessage = "Saving markings...";
                
                await _databaseService.UpdateSampleMarkingsAsync(
                    SelectedCoin.Id,
                    sample.ObverseImage ?? "",
                    sample.IsHolder,
                    sample.IsCounterstamped,
                    sample.IsRoll,
                    sample.ContainsHolder,
                    sample.ContainsText,
                    sample.IsMultiCoin
                );
                
                StatusMessage = "Markings saved successfully";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Failed to save markings: {ex.Message}";
                System.Diagnostics.Debug.WriteLine($"Save markings error: {ex}");
            }
        }

        private bool CanImportFromUcoin()
        {
            return SelectedCoin != null;
        }

        [RelayCommand(CanExecute = nameof(CanImportFromUcoin))]
        private void ImportFromUcoin()
        {
            if (SelectedCoin == null) return;
            
            StatusMessage = $"Import from ucoin for: {SelectedCoin.Title}";
            
            // TODO: Implement ucoin import logic
            System.Windows.MessageBox.Show(
                $"Import from ucoin functionality will be implemented here.\n\nSelected coin: {SelectedCoin.Title}",
                "Import from ucoin",
                System.Windows.MessageBoxButton.OK,
                System.Windows.MessageBoxImage.Information
            );
        }

        [RelayCommand(CanExecute = nameof(CanImportFromUcoin))]
        private async Task ChangeShape()
        {
            if (SelectedCoin == null || SelectedIssuer == null) return;

            try
            {
                StatusMessage = "Loading shape info...";
                
                // 1. Get Shapes from DB
                var shapes = await _databaseService.GetShapesAsync();
                
                // 2. Determine current values or try to parse
                int? currentShapeId = SelectedCoin.ShapeId;
                string? currentShapeInfo = SelectedCoin.ShapeInfo;

                if (currentShapeId == null && string.IsNullOrEmpty(currentShapeInfo))
                {
                    // Try to parse from HTML
                    try 
                    {
                        string htmlPath = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                        if (IO.File.Exists(htmlPath))
                        {
                            string html = await IO.File.ReadAllTextAsync(htmlPath);
                            var parsedData = _coinParserService.Parse(html);
                            
                            currentShapeInfo = parsedData.ShapeInfo;
                            
                            if (!string.IsNullOrEmpty(parsedData.Shape))
                            {
                                // Find ID by name
                                var shape = shapes.FirstOrDefault(s => s.Name.Equals(parsedData.Shape, StringComparison.OrdinalIgnoreCase));
                                if (shape != null)
                                {
                                    currentShapeId = shape.Id;
                                }
                                else
                                {
                                    // Maybe put unrecognized shape name into info?
                                    if (string.IsNullOrEmpty(currentShapeInfo)) currentShapeInfo = parsedData.Shape;
                                    else currentShapeInfo = $"{parsedData.Shape} {currentShapeInfo}";
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                         System.Diagnostics.Debug.WriteLine($"Error parsing html for shape: {ex.Message}");
                    }
                }

                // 3. Open Dialog
                await System.Windows.Application.Current.Dispatcher.InvokeAsync(async () => 
                {
                    var dialog = new ChangeCoinShapeDialog();
                    dialog.Owner = System.Windows.Application.Current.MainWindow;
                    dialog.SetData(shapes, currentShapeId, currentShapeInfo);
                    
                    if (dialog.ShowDialog() == true)
                    {
                        var newShape = dialog.SelectedShape;
                        var newInfo = dialog.ShapeInfo;
                        
                        // 4. Update DB
                        await _databaseService.UpdateCoinShapeAsync(SelectedCoin.Id, newShape?.Id, newInfo);
                        
                        // 5. Update Model
                        SelectedCoin.ShapeId = newShape?.Id;
                        SelectedCoin.ShapeInfo = newInfo;
                        
                        StatusMessage = "Shape updated.";
                    }
                    else
                    {
                        StatusMessage = "Change shape cancelled.";
                    }
                });
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error changing shape: {ex.Message}";
            }
        }

        private bool CanPromoteSample()
        {
             return SelectedCoin != null && 
                    SelectedSamples.Count == 1 && 
                    SelectedSamples[0].SampleType != 1;
        }

        [RelayCommand(CanExecute = nameof(CanSwapSample))]
        private async Task SwapSample()
        {
             if (SelectedCoin == null || SelectedIssuer == null || !SelectedSamples.Any()) return;
             
             // Snapshot list
             var samplesToProcess = SelectedSamples.ToList();

             foreach(var sample in samplesToProcess)
             {
                 if (string.IsNullOrEmpty(sample.ObversePath) || string.IsNullOrEmpty(sample.ReversePath)) continue;
                 // Double check constraint in loop
                 if (sample.IsCombinedImage) continue;
                 
                 try
                 {
                     // 1. DB Swap
                     string obvName = sample.ObverseImage ?? System.IO.Path.GetFileName(sample.ObversePath);
                     string revName = sample.ReverseImage ?? System.IO.Path.GetFileName(sample.ReversePath);
                     
                     await _databaseService.UpdateCoinSampleImagesAsync(SelectedCoin.Id, obvName, revName, obvName);
                     
                     // 2. HTML Swap
                     string htmlPath = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                     _fileService.SwapFullImageReferencesInHtml(htmlPath, obvName, revName);
                 }
                 catch (Exception ex)
                 {
                     StatusMessage = $"Error swapping sample: {ex.Message}";
                 }
             }

             // 3. Reload
             await LoadCoinsForIssuer(SelectedIssuer, SelectedCoin.Id);
        }

        private bool CanSwapSample()
        {
            return SelectedSamples.Any() && SelectedSamples.All(s => !s.IsCombinedImage && s.HasObverse && s.HasReverse);
        }

        [RelayCommand(CanExecute = nameof(CanChooseSample))]
        private async Task ChooseBestSample()
        {
            if (SelectedCoin == null || SelectedIssuer == null || SelectedSamples.Count < 2) return;

            var samples = SelectedSamples.ToList();
            
            // 1. Determine Survivor
            // Order by: Resolution Desc, IsReference Desc, FileSize Desc, ObverseName Asc
            var survivor = samples
                .OrderByDescending(s => GetImageResolution(s.ObversePath))
                .ThenByDescending(s => s.SampleType == 1) // true > false
                .ThenByDescending(s => GetFileSize(s.ObversePath))
                .ThenBy(s => s.ObverseImage)
                .First();

            var losers = samples.Where(s => s != survivor).ToList();
            
            try 
            {
                string htmlPath = _fileService.GetCoinHtmlPath(SelectedIssuer.UrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                
                bool keptType3Row = (survivor.SampleType == 3);
                
                foreach(var loser in losers)
                {
                   string loserObvName = loser.ObverseImage ?? System.IO.Path.GetFileName(loser.ObversePath);
                   string loserRevName = loser.ReverseImage ?? System.IO.Path.GetFileName(loser.ReversePath);
                   
                   // 2. Soft Delete in DB
                   await _databaseService.SoftDeleteCoinSampleAsync(SelectedCoin.Id, loserObvName);
                   
                   // 3. Backup HTML (if not exists) & Update HTML References
                   // _fileService needs UpdateReference(html, old, new)
                   string survivorObvName = survivor.ObverseImage ?? System.IO.Path.GetFileName(survivor.ObversePath);
                   string survivorRevName = survivor.ReverseImage ?? System.IO.Path.GetFileName(survivor.ReversePath); // Could be same if combined
                   
                   // 3. Update HTML: Collapse Type 3 rows.
                   // Goal: Keep exactly one Type 3 row for the group. 
                   // If Survivor is Type 3, we keep it (implicitly).
                   // If Survivor is Type 1, we keep the FIRST Type 3 loser and update it.
                   // All other Type 3 losers are removed.
                   
                   bool isType3 = (loser.SampleType == 3);
                   
                   if (isType3 && keptType3Row)
                   {
                       // Already have a Type 3 row (Survivor or a previous Loser) -> Delete this one
                       // Type 3 entries are in individual <tbody>s with copyright rows. 
                       // We must remove the entire tbody to avoid artifacts.
                       if (!string.IsNullOrEmpty(loserObvName))
                           _fileService.RemoveSaleTableBody(htmlPath, loserObvName);
                   }
                   else
                   {
                        // Keep this row (Update Reference)
                        if (isType3) keptType3Row = true;
                        
                        _fileService.UpdateImageReferenceInHtml(htmlPath, loserObvName, survivorObvName);
                        if (!string.IsNullOrEmpty(loserRevName) && !string.IsNullOrEmpty(survivorRevName) && loserRevName != loserObvName)
                        {
                            _fileService.UpdateImageReferenceInHtml(htmlPath, loserRevName, survivorRevName);
                        }
                   }
                   
                   // 4. Move Loser Files to Backup
                   _fileService.MoveToBackup(loser.ObversePath);
                   if (loser.ReversePath != loser.ObversePath)
                        _fileService.MoveToBackup(loser.ReversePath);
                }
                
                // 5. Promote Survivor if needed
                // If we deleted a Type 1, and Survivor is NOT Type 1, promote it.
                bool deletedType1 = losers.Any(s => s.SampleType == 1);
                if (deletedType1 && survivor.SampleType != 1)
                {
                    string survObv = survivor.ObverseImage ?? System.IO.Path.GetFileName(survivor.ObversePath);
                    await _databaseService.UpdateCoinSampleTypeAsync(SelectedCoin.Id, survObv, 1);
                }
                
                await LoadCoinsForIssuer(SelectedIssuer, SelectedCoin.Id);
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error choosing sample: {ex.Message}";
            }
        }

        private bool CanChooseSample()
        {
            return SelectedSamples.Count > 1;
        }

        private long GetImageResolution(string path)
        {
            try
            {
                 if (!IO.File.Exists(path)) return 0;
                 using var fs = new IO.FileStream(path, IO.FileMode.Open, IO.FileAccess.Read);
                 var decoder = System.Windows.Media.Imaging.BitmapDecoder.Create(fs, System.Windows.Media.Imaging.BitmapCreateOptions.PreservePixelFormat, System.Windows.Media.Imaging.BitmapCacheOption.OnLoad);
                 var frame = decoder.Frames[0];
                 return (long)frame.PixelWidth * frame.PixelHeight;
            }
            catch { return 0; }
        }

        private long GetFileSize(string path)
        {
             if (!IO.File.Exists(path)) return 0;
             return new IO.FileInfo(path).Length;
        }

        private async Task LoadRulersForIssuer(Issuer issuer)
        {
            try
            {
                StatusMessage = $"Loading rulers for {issuer.Name}...";
                var rulers = await _databaseService.GetRulersForIssuerAsync(issuer.Id);
                
                var grouped = new List<RulerPeriodGroup>();
                
                // Group rulers with periods
                var rulersWithPeriod = rulers.Where(r => !string.IsNullOrWhiteSpace(r.Period));
                var periodGroups = rulersWithPeriod
                    .GroupBy(r => new { r.Period, r.PeriodOrder })
                    .Select(g => {
                        var allAssociated = g.All(r => r.IssuerId == issuer.Id);
                        var someAssociated = g.Any(r => r.IssuerId == issuer.Id);
                        
                        return new RulerPeriodGroup
                        {
                            Period = g.Key.Period,
                            PeriodOrder = g.Key.PeriodOrder,
                            Rulers = g.ToList(),
                            IsAssociated = allAssociated,
                            IsPartiallyAssociated = someAssociated && !allAssociated
                        };
                    });
                grouped.AddRange(periodGroups);
                
                // Add rulers without period as individual "groups" (will be displayed without expander)
                var rulersWithoutPeriod = rulers.Where(r => string.IsNullOrWhiteSpace(r.Period));
                foreach (var ruler in rulersWithoutPeriod)
                {
                    grouped.Add(new RulerPeriodGroup
                    {
                        Period = "", // Empty period means no grouping header
                        Rulers = new List<Ruler> { ruler }
                    });
                }
                
                Rulers = new ObservableCollection<RulerPeriodGroup>(grouped);
                StatusMessage = $"Loaded {rulers.Count} ruler(s).";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error loading rulers: {ex.Message}";
            }
        }
        
        private async Task AutoAssociateAndLoadRulers(Issuer issuer)
        {
            try
            {
                await _databaseService.AutoAssociateRulersWithIssuerAsync(issuer.Id);
                await LoadRulersForIssuer(issuer);
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error auto-associating rulers: {ex.Message}";
                // Try to load rulers anyway
                await LoadRulersForIssuer(issuer);
            }
        }

        [RelayCommand]
        private async Task ToggleRulerAssociation(Ruler ruler)
        {
            if (SelectedIssuer == null) return;
            
            try
            {
                StatusMessage = "Toggling association...";
                var newIssuerId = ruler.IssuerId == SelectedIssuer.Id ? (long?)null : SelectedIssuer.Id;
                await _databaseService.ToggleRulerAssociationAsync(ruler.RowId, newIssuerId);
                await LoadRulersForIssuer(SelectedIssuer);
                StatusMessage = "Association updated.";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error toggling ruler: {ex.Message}";
            }
        }

        [RelayCommand]
        private async Task TogglePeriodGroupAssociation(RulerPeriodGroup group)
        {
            if (SelectedIssuer == null) return;
            
            try
            {
                StatusMessage = "Toggling group association...";
                bool associate = !group.IsAssociated;
                await _databaseService.TogglePeriodGroupAssociationAsync(
                    SelectedIssuer.Id, 
                    group.Period,
                    group.PeriodOrder,
                    associate
                );
                await LoadRulersForIssuer(SelectedIssuer);
                StatusMessage = "Group association updated.";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error toggling group: {ex.Message}";
            }
        }



        private System.Threading.CancellationTokenSource? _loadCoinsCts;

        private async Task LoadCoinsForIssuer(Issuer issuer, long? preserveCoinId = null, bool exclusiveCoin = false)
        {
            // Cancel previous load
            _loadCoinsCts?.Cancel();
            _loadCoinsCts = new System.Threading.CancellationTokenSource();
            var token = _loadCoinsCts.Token;



            try 
            {
                StatusMessage = $"Loading coins for {issuer.Name}...";
                
                // Capture filter states to use in background thread
                bool filterNonRef = IsNonReferenceFilterActive;
                bool filterHidden = IsHideFixedFilterActive;
                long issuerId = issuer.Id;
                string issuerSlug = issuer.UrlSlug;
                
                long? exclusiveIdTarget = _exclusiveCoinId; // Capture persistent state
                
                // Capture file service reference for background usage
                var fileService = _fileService;

                var coins = await Task.Run(async () => 
                {
                    if (token.IsCancellationRequested) return new List<CoinType>();

                    var rawCoins = await _databaseService.GetCoinTypesAsync(issuerId, issuerSlug);
                    
                    if (token.IsCancellationRequested) return new List<CoinType>();

                    // Persistent Exclusive Filter
                    // If we have an active exclusive ID, and this issuer contains it, forced filter.
                    if (exclusiveIdTarget.HasValue)
                    {
                         if (rawCoins.Any(c => c.Id == exclusiveIdTarget.Value))
                         {
                             rawCoins = rawCoins.Where(c => c.Id == exclusiveIdTarget.Value).ToList();
                             // Continue to populate images for this coin
                         }
                    }

                    foreach(var coin in rawCoins)
                    {
                        if (token.IsCancellationRequested) break;
                        
                        // Use FileService to populate paths
                        string coinDir = fileService.GetCoinDirectory(issuerSlug, coin.CoinTypeSlug, coin.Id);
                        string imagesDir = System.IO.Path.Combine(coinDir, "images");
                        
                        // Use ObservableCollection constructor for thread safety preparation
                        foreach(var sample in coin.Samples)
                        {
                            if (!string.IsNullOrEmpty(sample.ObverseImage))
                               sample.ObversePath = System.IO.Path.Combine(imagesDir, sample.ObverseImage);
                               
                            if (!string.IsNullOrEmpty(sample.ReverseImage))
                               sample.ReversePath = System.IO.Path.Combine(imagesDir, sample.ReverseImage);
                        }
                        
                        coin.Samples = new System.Collections.ObjectModel.ObservableCollection<CoinSample>(coin.Samples.OrderBy(s => s.SampleType == 1 ? 0 : 1));
                    }
                    
                    if (token.IsCancellationRequested) return new List<CoinType>();
                    
                    // Filter Logic (if not exclusive)
                    if (!exclusiveIdTarget.HasValue)
                    {
                        // Filter
                        if (filterNonRef)
                        {
                            var keepIds = await _databaseService.GetIssuersWithNonReferenceSamplesAsync();
                            // This logic seems wrong. GetIssuersWithNonReferenceSamplesAsync returns ISSUER IDs.
                            // We need to filter COINS here.
                            // Actually, DatabaseService.GetCoinTypesAsync already returns sample info.
                            // Let's filter in-memory based on Sample properties.
                             rawCoins = rawCoins.Where(c => c.NonReferenceSamples.Any()).ToList();
                        }

                        if (filterHidden)
                        {
                            rawCoins = rawCoins.Where(c => !c.IsFixed).ToList();
                        }
                    }

                    return rawCoins;
                }, token);

                if (token.IsCancellationRequested) return;

                Coins = new ObservableCollection<CoinType>(coins);

                // Run Fuzzy Analysis in background
                _ = Task.Run(() => AnalyzeFuzzyGroups(coins));
                
                StatusMessage = $"Loaded {coins.Count} coins for {issuer.Name}.";

                if (Coins.Any())
                {
                    if (preserveCoinId.HasValue)
                    {
                         var target = Coins.FirstOrDefault(c => c.Id == preserveCoinId.Value);
                         if (target != null)
                         {
                             SelectedCoin = target;
                             StatusMessage = $"Selected found coin: {target.Title}";
                         }
                         else
                         {
                             StatusMessage = $"Coin {preserveCoinId} not found in filtered list. Selecting first.";
                             SelectedCoin = Coins.First();
                         }
                    }
                    else
                    {
                        StatusMessage = $"Selecting first coin: {Coins.First().Title}";
                        SelectedCoin = Coins.First();
                    }
                }
            }
            catch (OperationCanceledException) { }
            catch (Exception ex)
            {
                StatusMessage = $"Error loading coins: {ex.Message}";
            }
        }

        private async Task AnalyzeFuzzyGroups(List<CoinType> coins)
        {
            try
            {
                foreach (var coin in coins)
                {
                    var coinSamples = coin.Samples.Where(s => !s.IsCombinedImage && s.HasObverse).ToList();
                    var hashes = new Dictionary<CoinSample, ulong>();

                    // 1. Compute Hashes
                    foreach (var sample in coinSamples)
                    {
                        if (string.IsNullOrEmpty(sample.ObversePath)) continue;
                        // Optimization: Check if DHash is already computed/cached in model? 
                        // CoinSample has DHash property but we weren't using it for persistence, only temp.
                        // We can recalculate. Ideally we should store it in CoinSample to avoid recalc if called again.
                        
                        var hash = await _imageAnalysisService.ComputeDHashAsync(sample.ObversePath);
                        if (hash.HasValue)
                        {
                            hashes[sample] = hash.Value;
                        }
                    }

                    // 2. Group within this coin
                    int groupId = 1;
                    var processed = new HashSet<CoinSample>();
                    var samplesList = hashes.Keys.ToList();

                    for (int i = 0; i < samplesList.Count; i++)
                    {
                        var current = samplesList[i];
                        if (processed.Contains(current)) continue;

                        var group = new List<CoinSample> { current };
                        
                        for (int j = i + 1; j < samplesList.Count; j++)
                        {
                            var other = samplesList[j];
                            if (processed.Contains(other)) continue;

                            int dist = _imageAnalysisService.CalculateHammingDistance(hashes[current], hashes[other]);
                            if (dist <= 9) 
                            {
                                group.Add(other);
                            }
                        }

                        if (group.Count > 1)
                        {
                            foreach (var sample in group)
                            {
                                await System.Windows.Application.Current.Dispatcher.InvokeAsync(() => 
                                {
                                    sample.FuzzyGroupIndex = groupId;
                                });
                                processed.Add(sample);
                            }
                            groupId++;
                        }
                        processed.Add(current);
                    }
                }
            }
            catch (Exception ex)
            {
                // Silently fail or log?
                System.Diagnostics.Debug.WriteLine($"Fuzzy analysis error: {ex.Message}");
            }
        }

        private void BuildHierarchy()
        {
            var lookup = _allIssuers.GroupBy(i => i.UrlSlug).ToDictionary(g => g.Key, g => g.First());
            
            foreach(var issuer in _allIssuers)
            {
                issuer.Children.Clear(); 
            }

            var roots = new List<Issuer>();
            foreach(var issuer in _allIssuers)
            {
                if (string.IsNullOrEmpty(issuer.ParentUrlSlug))
                {
                    roots.Add(issuer);
                }
                else
                {
                    if (lookup.TryGetValue(issuer.ParentUrlSlug, out var parent))
                    {
                        parent.Children.Add(issuer);
                    }
                    else
                    {
                        roots.Add(issuer); 
                    }
                }
            }
            
            _rootIssuers = roots;
        }

        private async Task FilterIssuers()
        {
            // Always get issuers with coins to ensure we never show empty issuers
            HashSet<long> validIssuerIds = null;
            
            // Only show text filter message if there's actual text filtering
            if (!string.IsNullOrWhiteSpace(FilterText) || IsNonReferenceFilterActive || IsHideFixedFilterActive || IsShowCompletedFilterActive)
            {
                StatusMessage = "Filtering issuers...";
            }
            
            // Always get issuers that have at least one coin type
            validIssuerIds = await _databaseService.GetIssuerIdsWithCoinsAsync(
                IsNonReferenceFilterActive, 
                IsHideFixedFilterActive, 
                IsShowCompletedFilterActive
            );
            
            StatusMessage = "Ready.";

            var filtered = new List<Issuer>();
            foreach (var issuer in _rootIssuers)
            {
                var match = FilterIssuerRecursive(issuer, validIssuerIds);
                if (match != null)
                {
                    filtered.Add(match);
                }
            }
            Issuers = new ObservableCollection<Issuer>(filtered);

            // Filter Leaf Issuers
            if (string.IsNullOrWhiteSpace(FilterText))
            {
                LeafIssuers = new ObservableCollection<LeafIssuerViewModel>(_allLeafIssuers);
            }
            else
            {
                var filteredLeaves = _allLeafIssuers
                    .Where(l => l.FullPath.Contains(FilterText, StringComparison.OrdinalIgnoreCase))
                    .ToList();
                LeafIssuers = new ObservableCollection<LeafIssuerViewModel>(filteredLeaves);
            }
        }



        [RelayCommand]
        private async Task SearchByCoinId()
        {
            if (string.IsNullOrWhiteSpace(SearchCoinIdText) || !long.TryParse(SearchCoinIdText, out long coinId))
            {
                StatusMessage = "Invalid Coin ID format.";
                return;
            }

            try
            {
                StatusMessage = $"Searching for Coin ID: {coinId}...";
                var issuerId = await _databaseService.GetIssuerIdByCoinTypeIdAsync(coinId);
                
                if (issuerId.HasValue)
                {
                    // Find the issuer in our tree
                    // Flatten the tree or search recursively?
                    // We have _allIssuers list which is flat but hierarchically linked.
                    // Or we can find it in _allIssuers easily since it contains ALL issuers.
                    
                    var issuer = _allIssuers.FirstOrDefault(i => i.Id == issuerId.Value);
                    if (issuer != null)
                    {
                        // We need to ensure the parent path is expanded if it's a child?
                        // The current UI logic uses `Issuers` (ObservableCollection) which is a filtered view of `_rootIssuers`.
                        // If we are filtering, we might need to clear filter to see it?
                        // For now, let's assume we select it.
                        
                        // Check if we need to clear filter to make it visible
                if (!string.IsNullOrEmpty(FilterText)) FilterText = string.Empty;
                if (IsNonReferenceFilterActive) IsNonReferenceFilterActive = false;
                if (IsHideFixedFilterActive) IsHideFixedFilterActive = false;
                if (IsShowCompletedFilterActive) IsShowCompletedFilterActive = false;
                
                // Allow a small yield to let property change handlers propagate/cancel?
                // Actually, the property setters trigger async loads. We want to supersede them.
                await Task.Delay(50);

                        // Select the issuer
                        SelectedIssuer = issuer;
                        
                        // Force load coins and select this specific coin
                        // LoadCoinsForIssuer is called by OnSelectedIssuerChanged, but we need to pass the coin ID.
                        // Wait, OnSelectedIssuerChanged calls LoadCoinsForIssuer(value) without coin ID.
                        // We should manually call it or update the logic.
                        
                        // Better approach: 
                        // 1. Set SelectedIssuer (triggers load)
                        // 2. Wait for load? Or call Load directly with ID?
                        
                        // If we set SelectedIssuer, it triggers OnSelectedIssuerChanged -> LoadCoinsForIssuer(value).
                        // But we want to select a specific coin.
                        // We can modify LoadCoinsForIssuer to take an optional coinId to select.
                        // But OnSelectedIssuerChanged doesn't pass it.
                        
                        // Let's call LoadCoinsForIssuer directly here properly?
                        // But setting SelectedIssuer will trigger the property changed handler.
                        // We can suppress property change or just let it happen and then re-do it?
                        // Or we can just call LoadCoinsForIssuer passing the ID, and update SelectedIssuer field directly (less clean).
                        
                        // Strategy:
                        // 1. Set SelectedIssuer.
                        // 2. The property setter triggers OnSelectedIssuerChanged.
                        // 3. OnSelectedIssuerChanged triggers LoadCoinsForIssuer(issuer).
                        // 4. This loads coins and selects the FIRST one.
                        // 5. We want to select `coinId`.
                        
                        // Problem: The async void/Task nature of the event handler makes it hard to wait for the automatic load.
                        // Solution: We can just call LoadCoinsForIssuer explicitly here with the ID.
                        // But we also need to update the UI selection for the Issuer.
                        
                        // If we just set SelectedIssuer, the UI updates. The handler starts a task. 
                        // If we fire another task immediately, they might race.
                        
                        // Let's rely on a slightly different mechanism or just accept we might load twice?
                        // OR, we can just call LoadCoinsForIssuer(issuer, coinId) directly and THEN set _selectedIssuer backing field and notify?
                        // If we set _selectedIssuer and Notify, the handler still fires? 
                        // No, if we set the field and call OnPropertyChanged, it fires.
                        // If we set the field only? UI won't update.
                        
                        // Let's just update the LoadCoinsForIssuer to be robust, and here:
                        // We will set a temporary 'target coin id' flag or similar? No, that's messy.
                        
                        // How about we just call LoadCoinsForIssuer(issuer, coinId) MANUALLY here.
                        // And we set SelectedIssuer property.
                        // Getting around the "OnChanged" double load:
                        // We can check if the issuer is ALREADY selected.
                        

                             // If we change it, the Handler fires. 
                             // We can use a flag `_isNavigatingToCoin`? 
                             // Or just let it load, and then we select the coin after?

                // Exclusive search mode - Set Persistent ID
                _exclusiveCoinId = coinId;

                // Batch clear filters (Performance optimization)
                _suppressFilterChanges = true;
                bool filtersWereActive = !string.IsNullOrEmpty(FilterText) || IsNonReferenceFilterActive || IsHideFixedFilterActive || IsShowCompletedFilterActive;
                
                FilterText = string.Empty;
                IsNonReferenceFilterActive = false;
                IsHideFixedFilterActive = false;
                IsShowCompletedFilterActive = false;
                
                _suppressFilterChanges = false;
                
                if (filtersWereActive)
                {
                     // Manually trigger ONE filter update now that batch is done
                     _activeFilteringTask = FilterIssuers(); 
                     await _activeFilteringTask;
                }

                // Find the issuer instance in the current View collection (Issuers)
                var targetIssuer = FindIssuerById(Issuers, issuerId.Value);

                if (targetIssuer != null)
                {
                    _pendingCoinSelectionId = coinId;
                        
                    if (SelectedIssuer == targetIssuer)
                    {
                        // Explicitly reload because property setter won't trigger change
                        await LoadCoinsForIssuer(targetIssuer, coinId); 
                    }
                    else
                    {
                        // Select the issuer - this triggers OnSelectedIssuerChanged
                        SelectedIssuer = targetIssuer;
                    }
                    
                    StatusMessage = $"Found Coin {coinId} in {targetIssuer.Name}.";
                }
                else
                {
                    // Fallback if not found in tree
                    _exclusiveCoinId = null; 
                    StatusMessage = "Issuer found but could not be located in the tree.";
                }

            }

            }
            else
            {
                StatusMessage = "Coin ID not found.";
            }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error searching: {ex.Message}";
            }
        }

        private Issuer? FilterIssuerRecursive(Issuer issuer, HashSet<long>? validIssuerIds)
        {
            bool textMatch = string.IsNullOrWhiteSpace(FilterText) || 
                             issuer.Name.Contains(FilterText, StringComparison.OrdinalIgnoreCase);
                             
            bool contentMatch = true;
            if (validIssuerIds != null)
            {
                contentMatch = validIssuerIds.Contains(issuer.Id);
            }

            var filteredChildren = new List<Issuer>();
            foreach (var child in issuer.Children)
            {
                var match = FilterIssuerRecursive(child, validIssuerIds);
                if (match != null)
                {
                    filteredChildren.Add(match);
                }
            }
            
            bool isSelfVisible = textMatch && contentMatch;
            bool hasVisibleChildren = filteredChildren.Any();

            if (isSelfVisible || hasVisibleChildren)
            {
                 var viewIssuer = new Issuer
                 {
                     Id = issuer.Id,
                     Name = issuer.Name,
                     UrlSlug = issuer.UrlSlug,
                     ParentUrlSlug = issuer.ParentUrlSlug,
                     HasNonReferenceSamples = issuer.HasNonReferenceSamples,
                     Children = filteredChildren
                 };
                 return viewIssuer;
            }
            return null;
        }

        private Issuer? FindIssuerById(IEnumerable<Issuer> nodes, long id)
        {
            foreach (var node in nodes)
            {
                if (node.Id == id) return node;
                if (node.Children != null)
                {
                    var found = FindIssuerById(node.Children, id);
                    if (found != null) return found;
                }
            }
            return null;
        }
        private async Task BuildLeafIssuers()
        {
            var validIssuerIds = await _databaseService.GetIssuerIdsWithRulersFromNewTableAsync();
            var leaves = new List<LeafIssuerViewModel>();
            foreach (var root in _rootIssuers)
            {
                TraverseForLeaves(root, root.Name, leaves, validIssuerIds);
            }
            _allLeafIssuers = leaves.OrderBy(l => l.FullPath).ToList();
        }

        private void TraverseForLeaves(Issuer node, string path, List<LeafIssuerViewModel> leaves, HashSet<long> validIssuerIds)
        {
            if (node.Children == null || node.Children.Count == 0)
            {
                // Leaf - only add if it has rulers
                if (validIssuerIds.Contains(node.Id))
                {
                    leaves.Add(new LeafIssuerViewModel(node.Id, path, LoadRulersForLeafCallback));
                }
            }
            else
            {
                foreach (var child in node.Children)
                {
                    TraverseForLeaves(child, path + " -> " + child.Name, leaves, validIssuerIds);
                }
            }
        }

        private async Task<List<RulerPeriodGroup>> LoadRulersForLeafCallback(long issuerId)
        {
            var rulers = await _databaseService.GetRulersForIssuerFromNewTableAsync(issuerId);
            
            // Group logic (simplified from LoadRulersForIssuer)
            var grouped = new List<RulerPeriodGroup>();
            var rulersWithPeriod = rulers.Where(r => !string.IsNullOrWhiteSpace(r.Period));
            var periodGroups = rulersWithPeriod
                .GroupBy(r => new { r.Period, r.PeriodOrder }) 
                .Select(g => new RulerPeriodGroup
                {
                    Period = g.Key.Period,
                    Rulers = g.ToList(),
                    IsAssociated = true, 
                    IsPartiallyAssociated = false
                });
            grouped.AddRange(periodGroups);

            var rulersWithoutPeriod = rulers.Where(r => string.IsNullOrWhiteSpace(r.Period));
            foreach (var ruler in rulersWithoutPeriod)
            {
                grouped.Add(new RulerPeriodGroup
                {
                    Period = "", 
                    Rulers = new List<Ruler> { ruler },
                    IsAssociated = true
                });
            }
            
            return grouped;
        }
        [RelayCommand]
        private async Task ChangeCoinShapeAsync()
        {
            if (SelectedCoin == null) return;

            var shapes = await _databaseService.GetShapesAsync();
            
            int? initialShapeId = SelectedCoin.ShapeId;
            string? initialShapeInfo = SelectedCoin.ShapeInfo;

            // Try to parse if missing
            if (initialShapeId == null && string.IsNullOrEmpty(initialShapeInfo))
            {
                try 
                {
                    if (!string.IsNullOrEmpty(SelectedCoin.IssuerUrlSlug) && !string.IsNullOrEmpty(SelectedCoin.CoinTypeSlug))
                    {
                         var htmlPath = _fileService.GetCoinHtmlPath(SelectedCoin.IssuerUrlSlug, SelectedCoin.CoinTypeSlug, SelectedCoin.Id);
                         if (IO.File.Exists(htmlPath))
                         {
                             var htmlContent = await IO.File.ReadAllTextAsync(htmlPath);
                             var data = _coinParserService.Parse(htmlContent);
                             
                             if (!string.IsNullOrEmpty(data.Shape))
                             {
                                 var match = shapes.FirstOrDefault(s => s.Name.Equals(data.Shape, StringComparison.OrdinalIgnoreCase));
                                 if (match != null)
                                 {
                                     initialShapeId = match.Id;
                                 }
                                 else
                                 {
                                     // If we differ from DB list, put everything in Info
                                     if (!string.IsNullOrEmpty(data.ShapeInfo)) 
                                         initialShapeInfo = $"{data.Shape}, {data.ShapeInfo}";
                                     else 
                                         initialShapeInfo = data.Shape;
                                 }
                             }
                             
                             if (!string.IsNullOrEmpty(data.ShapeInfo) && initialShapeId != null)
                             {
                                 initialShapeInfo = data.ShapeInfo;
                             }
                         }
                    }
                }
                catch { }
            }

            var dialog = new ChangeCoinShapeDialog();
            dialog.Owner = System.Windows.Application.Current.MainWindow;
            dialog.SetData(shapes, initialShapeId, initialShapeInfo);

            if (dialog.ShowDialog() == true)
            {
                var newShapeId = dialog.SelectedShape?.Id;
                var newShapeInfo = dialog.ShapeInfo;

                await _databaseService.UpdateCoinShapeAsync(SelectedCoin.Id, newShapeId, newShapeInfo);
                
                // If shape ID or logic changed, mark as fixed in shape_exceptions
                // Compare against the ORIGINAL DB values (SelectedCoin), not the potentially autofilled 'initial' values
                if (newShapeId != SelectedCoin.ShapeId || 
                    (newShapeInfo ?? string.Empty) != (SelectedCoin.ShapeInfo ?? string.Empty))
                {
                    await _databaseService.UpdateShapeExceptionFixedStatusAsync(SelectedCoin.Id, true);
                }
                
                SelectedCoin.ShapeId = newShapeId;
                SelectedCoin.ShapeInfo = newShapeInfo;
                
                // Refresh list item to update UI
                 var index = Coins.IndexOf(SelectedCoin);
                 if (index >= 0)
                 {
                     Coins[index] = SelectedCoin;
                     SelectedCoin = Coins[index];
                 }

                 // Update Verified Shape UI
                 if (ParsedData != null)
                 {
                     ParsedData.DbShapeId = newShapeId;
                     // Force property changed notification for ParsedData to refresh UI
                     OnPropertyChanged(nameof(ParsedData));
                 }
            }
        }
    }
}
