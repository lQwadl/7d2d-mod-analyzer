using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using ModManager.Backend.Engines;
using ModManager.Backend.Models;
using ModManager.Backend.Services;
using ModManagerPrototype;

namespace ModManager.Backend.Ports
{
    public static class PortHandlers
    {
        private static readonly ModScanner _scanner = new ModScanner();
        private static readonly LoadOrderEngine _loadOrder = new LoadOrderEngine();
        private static readonly ConflictEngine _conflicts = new ConflictEngine();
        private static readonly CategorizationEngine _categorizer = new CategorizationEngine();
        private static readonly BackendStateBuilder _stateBuilder = new BackendStateBuilder(_categorizer);

        private static readonly ProfileService _profiles = new ProfileService();
        private static readonly BackupService _backups = new BackupService();
        private static readonly DeploymentService _deploy = new DeploymentService();

        private static List<ModInfo> _allMods = new List<ModInfo>();
        private static List<ModInfo> _viewMods = new List<ModInfo>();

        private static string _lastModsRoot = string.Empty;
        private static List<ModConflictSummary> _lastConflicts = new List<ModConflictSummary>();
        private static BackendState _lastState = BackendState.Empty();
        private static int _lastScanDurationMs;

        private static string _lastSearchText = string.Empty;
        private static string _lastCategory = string.Empty;
        private static string _lastOrderType = string.Empty;
        private static string? _selectedModName;

        public static IUiPort? Ui { get; private set; }

        // Backend-triggered events (JSON only). UI subscribes and renders.
        public static event Action<string>? OnScanComplete;
        public static event Action<string>? OnConflictResolved;
        public static event Action<string>? OnLoadOrderChanged;
        public static event Action<string>? OnFilterApplied;
        public static event Action<string>? OnModStateChanged;

        // Backend-triggered port for direct object-graph snapshot (no JSON parsing, no file IO).
        public static event Action<PortData>? OnPortEmitted;

        private static readonly JsonSerializerOptions _stateJsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        };

        private static string _lastStateJson = JsonSerializer.Serialize(BackendState.Empty(), _stateJsonOptions);

        public static void Initialize(IUiPort ui)
        {
            Ui = ui;
        }

        public static async Task HandleScanModsAsync()
        {
            await RunLoggedAsync(nameof(HandleScanModsAsync), async () =>
            {
                var ui = RequireUi();
                var path = (ui.ModsPath ?? string.Empty).Trim();
                if (string.IsNullOrWhiteSpace(path))
                {
                    _lastModsRoot = string.Empty;
                    _allMods = new List<ModInfo>();
                    _lastConflicts = new List<ModConflictSummary>();
                    _lastState = BackendState.Empty("Mods path is empty");
                    _lastScanDurationMs = 0;
                    _lastStateJson = SerializeState(_lastState);
                    OnScanComplete?.Invoke(_lastStateJson);
                    ui.ShowWarning("Invalid Path", "Please provide a Mods path.");
                    return;
                }

                _lastModsRoot = path;

                var scanTimer = Stopwatch.StartNew();
                var scanned = await _scanner.ScanAsync(path);
                scanTimer.Stop();
                _lastScanDurationMs = (int)Math.Min(int.MaxValue, scanTimer.ElapsedMilliseconds);
                _allMods = new List<ModInfo>(scanned);

                // Reset view state on fresh scan.
                _lastSearchText = string.Empty;
                _lastCategory = string.Empty;
                _lastOrderType = string.Empty;
                _selectedModName = null;

                ApplyViewAndPush(ui);

                // Lightweight conflict analysis on scan (fast); deep scan occurs on explicit CheckConflicts.
                _lastConflicts = (await _conflicts.AnalyzeAsync(_lastModsRoot, _allMods, deepFileCollisionScan: false)).ToList();
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnScanComplete?.Invoke(_lastStateJson);
                PublishSnapshot("OnScanComplete");

                if (_allMods.Count == 0)
                    ui.ShowInfo("No Mods", "No mod folders found in the specified Mods path.");
            });
        }

        public static async Task HandleRefreshModsAsync() => await HandleScanModsAsync();

        public static async Task HandleGenerateLoadOrderAsync()
        {
            await RunLoggedAsync(nameof(HandleGenerateLoadOrderAsync), async () =>
            {
                var ui = RequireUi();

                // Always generate on the full set; view is derived.
                var ordered = await _loadOrder.GenerateAsync(_allMods);
                _allMods = new List<ModInfo>(ordered);

                // Update view ordering first, then build/publish snapshot from view.
                ApplyViewAndPush(ui);

                // Load order changes can affect violation checks.
                _lastConflicts = (await _conflicts.AnalyzeAsync(_lastModsRoot, _allMods, deepFileCollisionScan: false)).ToList();
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnLoadOrderChanged?.Invoke(_lastStateJson);
                PublishSnapshot("OnLoadOrderChanged");
            });
        }

        public static async Task HandleExportJsonAsync(string outputPath)
        {
            await RunLoggedAsync(nameof(HandleExportJsonAsync), async () =>
            {
                var ui = RequireUi();

                if (string.IsNullOrWhiteSpace(outputPath))
                {
                    ui.ShowWarning("Invalid Path", "Please choose a valid export file path.");
                    return;
                }

                var fileName = Path.GetFileName(outputPath);
                var isLoadOrderExport = fileName.Equals("loadOrder.json", StringComparison.OrdinalIgnoreCase)
                    || fileName.EndsWith(".loadorder.json", StringComparison.OrdinalIgnoreCase);

                if (isLoadOrderExport)
                {
                    var source = _allMods.Count > 0 ? _allMods : (_lastState?.Mods ?? new List<ModInfo>());
                    var payload = BuildLoadOrderExport(source);
                    var exportJson = JsonSerializer.Serialize(payload, _stateJsonOptions);
                    await File.WriteAllTextAsync(outputPath, exportJson);
                    ui.ShowInfo("Export Complete", "Exported grouped load order JSON successfully.");
                    return;
                }

                // Strict contract (camelCase) with backend-owned computed fields.
                // Always export structured dataset, never UI-specific formatting.
                BackendState state;
                try
                {
                    state = _lastState ?? BackendState.Empty();
                    if (state.Mods.Count == 0 && _allMods.Count > 0)
                    {
                        // Ensure we can still export even if state wasn't rebuilt for some reason.
                        state = _stateBuilder.Build(_allMods, _lastConflicts);
                    }

                    // If there's no scanned data, still export an empty dataset with structured error.
                    if (_allMods.Count == 0)
                        state = BackendState.Empty("No scanned mod data");
                }
                catch (Exception ex)
                {
                    PortLogger.Error("ExportJson: failed building state", ex);
                    state = BackendState.Empty("Failed to build backend dataset");
                }

                var json = SerializeState(state);
                await File.WriteAllTextAsync(outputPath, json);
                ui.ShowInfo("Export Complete", "Exported backend dataset JSON successfully.");
            });
        }

        public static async Task HandleExportVortexAsync(string outputPath)
        {
            await RunLoggedAsync(nameof(HandleExportVortexAsync), async () =>
            {
                var ui = RequireUi();

                if (string.IsNullOrWhiteSpace(outputPath))
                {
                    ui.ShowWarning("Invalid Path", "Please choose a valid export file path.");
                    return;
                }

                var source = _allMods.Count > 0 ? _allMods : (_lastState?.Mods ?? new List<ModInfo>());

                static string VortexId(ModInfo m)
                {
                    if (m == null) return string.Empty;
                    if (!string.IsNullOrWhiteSpace(m.FolderName)) return m.FolderName.Trim();
                    if (!string.IsNullOrWhiteSpace(m.Id)) return m.Id.Trim();
                    return (m.Name ?? string.Empty).Trim();
                }

                var vortexList = source
                    .Where(m => m != null && m.Enabled)
                    .OrderBy(m => m.LoadOrder)
                    .ThenBy(m => VortexId(m), StringComparer.OrdinalIgnoreCase)
                    .Select(m => new { id = VortexId(m), enabled = true })
                    .ToList();

                var json = JsonSerializer.Serialize(vortexList, _stateJsonOptions);
                await File.WriteAllTextAsync(outputPath, json);
                ui.ShowInfo("Export Complete", "Exported Vortex load order JSON successfully.");
            });
        }

        private static object BuildLoadOrderExport(IReadOnlyList<ModInfo> mods)
        {
            mods ??= Array.Empty<ModInfo>();

            string Display(ModInfo m)
            {
                if (!string.IsNullOrWhiteSpace(m.FolderName)) return m.FolderName.Trim();
                if (!string.IsNullOrWhiteSpace(m.Name)) return m.Name.Trim();
                return (m.Id ?? string.Empty).Trim();
            }

            string GroupFor(ModInfo m)
            {
                if (m == null) return "Uncategorized";
                if (!m.Enabled) return "Disabled";

                var tier = m.ResolvedTier;
                if (tier == ModTier.Core) return "Core";
                if (tier == ModTier.Library) return "UI and Utilities";
                if (tier == ModTier.Overhaul) return "Gameplay Mechanics";
                if (tier == ModTier.WorldGen) return "Environmental & Biomes";
                if (tier == ModTier.Patch) return "Patches";

                if (tier == ModTier.UI)
                {
                    // Separate late overrides from early UI deps/utilities.
                    if (m.IsUiOverride || m.UiOverrideRank >= 80 || m.UsesXpath || m.HasXml)
                        return "HUD/UI Overrides";
                    return "UI and Utilities";
                }

                // Content tier grouping using category text.
                var category = (m.Category ?? string.Empty).Trim();
                var categories = m.Categories ?? new List<string>();
                var catText = string.Join(" ", new[] { category }.Concat(categories)).ToLowerInvariant();

                if (catText.Contains("visual") || catText.Contains("audio") || catText.Contains("texture") || catText.Contains("sound") || catText.Contains("cosmetic") || catText.Contains("decor"))
                    return "Optional / Cosmetic";

                if (catText.Contains("biome") || catText.Contains("weather") || catText.Contains("environment") || catText.Contains("poi") || catText.Contains("prefab"))
                    return "Environmental & Biomes";

                if (catText.Contains("weapon") || catText.Contains("gun") || catText.Contains("combat") || catText.Contains("melee"))
                    return "Weapons and Combat";

                return "Gameplay Mechanics";
            }

            var ordered = mods
                .OrderBy(m => m.LoadOrder <= 0 ? int.MaxValue : m.LoadOrder)
                .ThenBy(m => m.FolderName ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                .ToList();

            var groupOrder = new[]
            {
                "Core",
                "UI and Utilities",
                "Gameplay Mechanics",
                "Weapons and Combat",
                "Environmental & Biomes",
                "Optional / Cosmetic",
                "HUD/UI Overrides",
                "Patches",
                "Disabled",
            };

            var buckets = groupOrder.ToDictionary(k => k, _ => new List<string>(), StringComparer.OrdinalIgnoreCase);

            foreach (var m in ordered)
            {
                var g = GroupFor(m);
                if (!buckets.TryGetValue(g, out var list))
                {
                    list = new List<string>();
                    buckets[g] = list;
                }
                list.Add(Display(m));
            }

            var groups = groupOrder
                .Select(name => new
                {
                    name,
                    mods = buckets.TryGetValue(name, out var list) ? list : new List<string>()
                })
                .Where(g => g.mods.Count > 0)
                .ToList();

            return new
            {
                schemaVersion = 1,
                generatedAtUtc = DateTime.UtcNow,
                totals = new
                {
                    mods = ordered.Count,
                    enabled = ordered.Count(m => m.Enabled),
                    disabled = ordered.Count(m => !m.Enabled)
                },
                groups
            };
        }

        public static async Task HandleConflictScanAsync()
        {
            await RunLoggedAsync(nameof(HandleConflictScanAsync), async () =>
            {
                var ui = RequireUi();

                // Deep collision scan (more expensive) only when explicitly requested.
                _lastConflicts = (await _conflicts.AnalyzeAsync(_lastModsRoot, _allMods, deepFileCollisionScan: true)).ToList();
                _lastState = _stateBuilder.Build(_viewMods.Count > 0 ? _viewMods : _allMods, _lastConflicts);

                _lastStateJson = SerializeState(_lastState);
                // Not a "resolved" event, but still a backend-triggered state change; reuse ScanComplete if UI wants a single hook.
                OnScanComplete?.Invoke(_lastStateJson);

                PublishSnapshot("OnConflictScan");

                ui.ShowInfo("Conflict Scan Complete", $"Detected {_lastConflicts.Sum(c => c.ConflictCount)} conflict signals across {_allMods.Count} mods.");
            });
        }

        public static async Task HandleResolveConflictsAsync()
        {
            await RunLoggedAsync(nameof(HandleResolveConflictsAsync), async () =>
            {
                var ui = RequireUi();
                await Task.CompletedTask;
                // Placeholder: once real resolution is implemented, this should rebuild state.
                OnConflictResolved?.Invoke(_lastStateJson);
                PublishSnapshot("OnConflictResolved");
                ui.ShowInfo("Not Implemented", "Conflict resolution is not implemented yet.");
            });
        }

        public static async Task HandleEnableAllModsAsync()
        {
            await RunLoggedAsync(nameof(HandleEnableAllModsAsync), async () =>
            {
                var ui = RequireUi();
                foreach (var mod in _allMods)
                    mod.Enabled = true;
                ApplyViewAndPush(ui);
                await Task.CompletedTask;
            });
        }

        public static async Task HandleDisableAllModsAsync()
        {
            await RunLoggedAsync(nameof(HandleDisableAllModsAsync), async () =>
            {
                var ui = RequireUi();
                foreach (var mod in _allMods)
                    mod.Enabled = false;
                ApplyViewAndPush(ui);
                await Task.CompletedTask;
            });
        }

        public static async Task HandleCreateProfileAsync()
        {
            await RunLoggedAsync(nameof(HandleCreateProfileAsync), async () =>
            {
                RequireUi();
                await _profiles.CreateProfileAsync();
            });
        }

        public static async Task HandleDeleteProfileAsync()
        {
            await RunLoggedAsync(nameof(HandleDeleteProfileAsync), async () =>
            {
                RequireUi();
                await _profiles.DeleteProfileAsync();
            });
        }

        public static async Task HandleSwitchProfileAsync(string profileName)
        {
            await RunLoggedAsync(nameof(HandleSwitchProfileAsync), async () =>
            {
                RequireUi();
                await _profiles.SwitchProfileAsync(profileName);
            });
        }

        public static async Task HandleBackupModsAsync()
        {
            await RunLoggedAsync(nameof(HandleBackupModsAsync), async () =>
            {
                RequireUi();
                await _backups.BackupModsAsync();
            });
        }

        public static async Task HandleRestoreBackupAsync()
        {
            await RunLoggedAsync(nameof(HandleRestoreBackupAsync), async () =>
            {
                RequireUi();
                await _backups.RestoreBackupAsync();
            });
        }

        public static async Task HandleDeployModsAsync()
        {
            await RunLoggedAsync(nameof(HandleDeployModsAsync), async () =>
            {
                RequireUi();
                await _deploy.DeployModsAsync();
            });
        }

        public static async Task HandleOpenModsFolderAsync()
        {
            await RunLoggedAsync(nameof(HandleOpenModsFolderAsync), async () =>
            {
                var ui = RequireUi();
                var path = (ui.ModsPath ?? string.Empty).Trim();
                if (string.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
                {
                    ui.ShowWarning("Invalid Path", "Mods folder path does not exist.");
                    return;
                }

                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = path,
                        UseShellExecute = true
                    });
                }
                catch (Exception ex)
                {
                    ui.ShowError("Error", "Failed to open Mods folder: " + ex.Message);
                }

                await Task.CompletedTask;
            });
        }

        public static async Task HandleSettingsAsync()
        {
            await RunLoggedAsync(nameof(HandleSettingsAsync), async () =>
            {
                var ui = RequireUi();
                await Task.CompletedTask;
                ui.ShowInfo("Not Implemented", "Settings UI/flow is not implemented yet.");
            });
        }

        public static async Task HandleModToggleAsync(string modName, bool enabled)
        {
            await RunLoggedAsync(nameof(HandleModToggleAsync), async () =>
            {
                var ui = RequireUi();
                if (string.IsNullOrWhiteSpace(modName))
                    return;

                var mod = _allMods.FirstOrDefault(m => NameEquals(m, modName));
                if (mod is null)
                    return;

                mod.Enabled = enabled;

                ApplyViewAndPush(ui);
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnModStateChanged?.Invoke(_lastStateJson);
                PublishSnapshot("OnModStateChanged");
                await Task.CompletedTask;
            });
        }

        public static async Task HandleModSelectionAsync(string modName)
        {
            await RunLoggedAsync(nameof(HandleModSelectionAsync), async () =>
            {
                RequireUi();
                _selectedModName = string.IsNullOrWhiteSpace(modName) ? null : modName;
                await Task.CompletedTask;
            });
        }

        public static async Task HandleSearchAsync(string text)
        {
            await RunLoggedAsync(nameof(HandleSearchAsync), async () =>
            {
                var ui = RequireUi();
                _lastSearchText = text ?? string.Empty;
                ApplyViewAndPush(ui);
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnFilterApplied?.Invoke(_lastStateJson);
                PublishSnapshot("OnFilterApplied");
                await Task.CompletedTask;
            });
        }

        public static async Task HandleCategoryFilterAsync(string category)
        {
            await RunLoggedAsync(nameof(HandleCategoryFilterAsync), async () =>
            {
                var ui = RequireUi();
                _lastCategory = category ?? string.Empty;
                ApplyViewAndPush(ui);
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnFilterApplied?.Invoke(_lastStateJson);
                PublishSnapshot("OnFilterApplied");
                await Task.CompletedTask;
            });
        }

        public static async Task HandleSortOrderAsync(string orderType)
        {
            await RunLoggedAsync(nameof(HandleSortOrderAsync), async () =>
            {
                var ui = RequireUi();
                _lastOrderType = orderType ?? string.Empty;
                ApplyViewAndPush(ui);
                _lastState = _stateBuilder.Build(_viewMods, _lastConflicts);
                _lastStateJson = SerializeState(_lastState);
                OnFilterApplied?.Invoke(_lastStateJson);
                PublishSnapshot("OnFilterApplied");
                await Task.CompletedTask;
            });
        }

        /// <summary>
        /// Port: UI requests the latest backend snapshot; backend emits it via OnPortEmitted.
        /// No file IO, no JSON parsing.
        /// </summary>
        public static async Task HandleGetBackendSnapshotAsync()
        {
            await RunLoggedAsync(nameof(HandleGetBackendSnapshotAsync), async () =>
            {
                RequireUi();
                PublishSnapshot("GetBackendSnapshot");
                await Task.CompletedTask;
            });
        }

        private static string SerializeState(BackendState state)
        {
            try
            {
                return JsonSerializer.Serialize(state ?? BackendState.Empty("State was null"), _stateJsonOptions);
            }
            catch (Exception ex)
            {
                PortLogger.Error("SerializeState failed", ex);
                return JsonSerializer.Serialize(BackendState.Empty("Failed to serialize backend dataset"), _stateJsonOptions);
            }
        }

        private static void PublishSnapshot(string reason)
        {
            var state = _lastState ?? BackendState.Empty("No snapshot available");
            var snapshot = BuildUiSnapshot(state);
            var portData = new PortData
            {
                Port = PortContract.PortIds.GetBackendSnapshot,
                Data = snapshot
            };

            PortLogger.Info($"SnapshotStart reason={reason}");
            try
            {
                OnPortEmitted?.Invoke(portData);
                PortLogger.Info($"SnapshotEnd reason={reason}");
            }
            catch (Exception ex)
            {
                PortLogger.Error($"SnapshotFail reason={reason}", ex);
            }
        }

        private static BackendSnapshot BuildUiSnapshot(BackendState state)
        {
            state ??= BackendState.Empty("State was null");

            var uiCategories = new List<CategorySnapshot>();
            if (state.Categories != null)
            {
                foreach (var c in state.Categories)
                {
                    if (c == null)
                        continue;

                    var total = c.ModCount;
                    var sev = c.SeverityDistribution ?? new SeverityDistribution();

                    var severityCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
                    {
                        ["Critical"] = sev.Critical,
                        ["High"] = sev.High,
                        ["Low"] = sev.Low,
                        ["Redundant"] = sev.Redundant,
                        ["Disabled"] = sev.Disabled,
                        ["OK"] = sev.OK
                    };

                    double Pct(int count) => total <= 0 ? 0.0 : (double)count / total * 100.0;

                    var percentages = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                    {
                        ["Critical"] = Pct(sev.Critical),
                        ["High"] = Pct(sev.High),
                        ["Low"] = Pct(sev.Low),
                        ["Redundant"] = Pct(sev.Redundant),
                        ["Disabled"] = Pct(sev.Disabled),
                        ["OK"] = Pct(sev.OK)
                    };

                    uiCategories.Add(new CategorySnapshot
                    {
                        Category = c.Name ?? string.Empty,
                        TotalMods = total,
                        Severity = severityCounts,
                        Percentages = percentages
                    });
                }
            }

            List<ModInfo>? mods = null;
            if (state.Mods != null)
                mods = state.Mods.Select(m => m?.DeepClone()).Where(m => m != null).ToList()!;

            ErrorSnapshot? err = null;
            if (state.Error != null && (!string.IsNullOrWhiteSpace(state.Error.Message) || !string.IsNullOrWhiteSpace(state.Error.Code) || !string.IsNullOrWhiteSpace(state.Error.Details)))
            {
                err = new ErrorSnapshot
                {
                    Code = state.Error.Code ?? string.Empty,
                    Message = state.Error.Message ?? string.Empty,
                    Details = state.Error.Details ?? string.Empty
                };
            }

            return new BackendSnapshot
            {
                SchemaVersion = 1,
                Categories = uiCategories,
                Totals = new TotalsSnapshot
                {
                    Mods = state.Totals?.Mods ?? 0,
                    Enabled = state.Totals?.Enabled ?? 0,
                    Disabled = state.Totals?.Disabled ?? 0,
                    Conflicts = state.Totals?.Conflicts ?? 0
                },
                Meta = new MetaSnapshot
                {
                    GeneratedAt = DateTime.UtcNow.ToString("O"),
                    ScanDurationMs = _lastScanDurationMs
                },
                Mods = mods,
                Error = err
            };
        }

        private static IUiPort RequireUi()
        {
            var ui = Ui;
            if (ui is null)
                throw new InvalidOperationException("PortHandlers.Initialize(IUiPort) must be called before using port handlers.");
            return ui;
        }

        private static bool NameEquals(ModInfo mod, string name)
        {
            return string.Equals(mod.Name, name, StringComparison.OrdinalIgnoreCase)
                || string.Equals(mod.FolderName, name, StringComparison.OrdinalIgnoreCase);
        }

        private static void ApplyViewAndPush(IUiPort ui)
        {
            IEnumerable<ModInfo> query = _allMods;

            if (!string.IsNullOrWhiteSpace(_lastCategory))
            {
                var normalized = CategoryNames.Normalize(_lastCategory);
                query = query.Where(m =>
                    (m.Categories != null && m.Categories.Any(c => string.Equals(c, normalized, StringComparison.OrdinalIgnoreCase)))
                    || string.Equals(m.Category ?? string.Empty, normalized, StringComparison.OrdinalIgnoreCase));
            }

            if (!string.IsNullOrWhiteSpace(_lastSearchText))
            {
                var needle = _lastSearchText.Trim();
                query = query.Where(m =>
                    (!string.IsNullOrEmpty(m.Name) && m.Name.Contains(needle, StringComparison.OrdinalIgnoreCase))
                    || (!string.IsNullOrEmpty(m.FolderName) && m.FolderName.Contains(needle, StringComparison.OrdinalIgnoreCase)));
            }

            // Sort order: keep it simple and deterministic.
            // Supported values are UI-defined; unknown values fall back to FolderName.
            if (string.Equals(_lastOrderType, "LoadOrder", StringComparison.OrdinalIgnoreCase))
            {
                query = query.OrderBy(m => m.LoadOrder).ThenBy(m => m.FolderName, StringComparer.OrdinalIgnoreCase);
            }
            else if (string.Equals(_lastOrderType, "Name", StringComparison.OrdinalIgnoreCase))
            {
                query = query.OrderBy(m => m.Name, StringComparer.OrdinalIgnoreCase).ThenBy(m => m.FolderName, StringComparer.OrdinalIgnoreCase);
            }
            else
            {
                query = query.OrderBy(m => m.FolderName, StringComparer.OrdinalIgnoreCase);
            }

            _viewMods = query.ToList();

            // Ensure categories are backend-owned and normalized even for UI grid.
            // Category is kept as the primary/first category for back-compat UI filtering.
            foreach (var mod in _viewMods)
            {
                if (mod.Categories is null || mod.Categories.Count == 0)
                {
                    mod.Categories = _categorizer.Categorize(mod).ToList();
                }
                mod.Category = mod.Categories.FirstOrDefault() ?? string.Empty;
            }

            ui.InvokeOnUi(() => ui.SetMods(_viewMods));
        }

        private static async Task RunLoggedAsync(string portName, Func<Task> action)
        {
            PortLogger.Info($"PortStart {portName}");
            try
            {
                await action();
                PortLogger.Info($"PortEnd {portName}");
            }
            catch (Exception ex)
            {
                PortLogger.Error($"PortFail {portName}", ex);

                // Best-effort: surface a generic error to UI.
                try
                {
                    Ui?.ShowError("Error", $"{portName} failed: {ex.Message}");
                }
                catch
                {
                    // ignore
                }

                throw;
            }
        }
    }
}
