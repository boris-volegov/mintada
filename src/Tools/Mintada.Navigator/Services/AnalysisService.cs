using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

using System.Collections.Concurrent;

namespace Mintada.Navigator.Services;

public class AnalysisService : IDisposable
{
    private Process? _pythonProcess;
    private StreamWriter? _inputStream;
    private TaskCompletionSource<string>? _responseTcs;
    private Task? _initTask;
    private readonly string _scriptPath;
    private readonly string _pythonPath;

    private bool _isReady;
    private readonly ConcurrentDictionary<string, bool> _cache = new();
    private readonly SemaphoreSlim _lock = new(1, 1);

    public AnalysisService(string scriptPath, string pythonPath = "python")
    {
        _scriptPath = scriptPath;
        _pythonPath = pythonPath;
    }

    public async Task StartAsync()
    {
        if (_isReady && _pythonProcess != null && !_pythonProcess.HasExited) return;
        
        // Return existing initialization if in progress
        if (_initTask != null && !_initTask.IsCompleted) 
        {
            await _initTask;
            return;
        }

        _initTask = InitializeAsync();
        await _initTask;
    }

    private async Task InitializeAsync()
    {
        try
        {
            Stop();

            var startInfo = new ProcessStartInfo
            {
                FileName = _pythonPath,
                Arguments = $"\"{_scriptPath}\" --interactive",
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = Path.GetDirectoryName(_scriptPath)
            };

            _pythonProcess = new Process { StartInfo = startInfo };
            _pythonProcess.OutputDataReceived += OnOutputDataReceived;
            _pythonProcess.ErrorDataReceived += (s, e) => { if (e.Data != null) Debug.WriteLine($"PYTHON ERR: {e.Data}"); };

            _pythonProcess.Start();
            _inputStream = _pythonProcess.StandardInput;
            _pythonProcess.BeginOutputReadLine();
            _pythonProcess.BeginErrorReadLine();

            // Wait for READY signal (30s timeout)
            _responseTcs = new TaskCompletionSource<string>();
            var firstMsg = await Task.WhenAny(_responseTcs.Task, Task.Delay(30000));
            
            if (firstMsg == _responseTcs.Task && _responseTcs.Task.Result == "READY")
            {
                _isReady = true;
                _responseTcs = null; // Reset for next command
            }
            else
            {
                Debug.WriteLine("Python script failed to start or timed out.");
                Stop();
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Error starting python: {ex}");
            Stop();
        }
    }

    private void OnOutputDataReceived(object sender, DataReceivedEventArgs e)
    {
        if (string.IsNullOrEmpty(e.Data)) return;
        Debug.WriteLine($"PYTHON OUT: {e.Data}");

        if (_responseTcs != null && !_responseTcs.Task.IsCompleted)
        {
            _responseTcs.TrySetResult(e.Data);
        }
    }

    public async Task<bool> CheckFlipAsync(string refObv, string refRev, string candObv, string candRev, CancellationToken token = default)
    {
        string key = $"{refObv}|{refRev}|{candObv}|{candRev}";
        if (_cache.TryGetValue(key, out bool cachedResult)) return cachedResult;

        // Acquire lock to ensure exclusive access to the Python process
        await _lock.WaitAsync(token);
        try
        {
            // Double check readiness inside lock
            if (!_isReady || _pythonProcess == null || _pythonProcess.HasExited)
            {
                 await StartAsync();
                 if (!_isReady) return false;
            }

            var payload = new
            {
                ref_obv = refObv,
                ref_rev = refRev,
                cand_obv = candObv,
                cand_rev = candRev
            };
    
            string json = JsonSerializer.Serialize(payload);
            
            _responseTcs = new TaskCompletionSource<string>();
            await _inputStream!.WriteLineAsync(json);
            await _inputStream.FlushAsync();
    
            var responseTask = await Task.WhenAny(_responseTcs.Task, Task.Delay(15000)); // 15s timeout
            
            if (responseTask == _responseTcs.Task)
            {
                string resultJson = _responseTcs.Task.Result;
                _responseTcs = null;
                
                try 
                {
                    // Debug Logging
                    try 
                    {
                         System.IO.File.AppendAllText(@"d:\projects\mintada\swap_debug.log", $"{DateTime.Now}: {resultJson}\n");
                    } 
                    catch { }

                    using var doc = JsonDocument.Parse(resultJson);
                    if (doc.RootElement.TryGetProperty("is_flip", out var prop))
                    {
                        bool isFlip = prop.GetBoolean();
                        _cache.TryAdd(key, isFlip);
                        return isFlip;
                    }
                }
                catch { }
            }
            else
            {
                Debug.WriteLine("Timeout waiting for python response.");
                _responseTcs = null;
            }
    
            return false;
        }
        finally
        {
            _lock.Release();
        }
    }

    public void Stop()
    {
        try
        {
            _pythonProcess?.Kill();
            _pythonProcess?.Dispose();
        }
        catch { }
        _pythonProcess = null;
        _isReady = false;
    }

    public void Dispose()
    {
        Stop();
        _lock.Dispose();
    }
}
