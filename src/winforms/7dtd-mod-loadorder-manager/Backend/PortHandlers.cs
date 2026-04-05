using System;
using System.Text.Json;
using System.Threading.Tasks;
using ModManager.Backend.Services;

namespace ModManagerPrototype
{
    /// <summary>
    /// Backend PortHandlers (stubs).
    ///
    /// Rules:
    /// - async Task only
    /// - no UI references
    /// - logging only (for now)
    /// - one method per PortContract action
    /// </summary>
    public static class PortHandlers
    {
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };

        public static async Task HandleScanMods()
        {
            PortLogger.Info("Handler HandleScanMods");
            Console.WriteLine("HandleScanMods triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleScanModsAsync();
        }

        public static async Task HandleRefreshMods()
        {
            PortLogger.Info("Handler HandleRefreshMods");
            Console.WriteLine("HandleRefreshMods triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleRefreshModsAsync();
        }

        public static async Task HandleEnableMod(object data)
        {
            PortLogger.Info("Handler HandleEnableMod");
            Console.WriteLine("HandleEnableMod triggered");
            var modName = ExtractModName(data);
            await ModManager.Backend.Ports.PortHandlers.HandleModToggleAsync(modName, true);
        }

        public static async Task HandleDisableMod(object data)
        {
            PortLogger.Info("Handler HandleDisableMod");
            Console.WriteLine("HandleDisableMod triggered");
            var modName = ExtractModName(data);
            await ModManager.Backend.Ports.PortHandlers.HandleModToggleAsync(modName, false);
        }

        public static async Task HandleGenerateLoadOrder()
        {
            PortLogger.Info("Handler HandleGenerateLoadOrder");
            Console.WriteLine("HandleGenerateLoadOrder triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleGenerateLoadOrderAsync();
        }

        public static async Task HandleCheckConflicts()
        {
            PortLogger.Info("Handler HandleCheckConflicts");
            Console.WriteLine("HandleCheckConflicts triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleConflictScanAsync();
        }

        public static async Task HandleResolveConflicts()
        {
            PortLogger.Info("Handler HandleResolveConflicts");
            Console.WriteLine("HandleResolveConflicts triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleResolveConflictsAsync();
        }

        public static async Task HandleCreateBackup()
        {
            PortLogger.Info("Handler HandleCreateBackup");
            Console.WriteLine("HandleCreateBackup triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleBackupModsAsync();
        }

        public static async Task HandleRestoreBackup()
        {
            PortLogger.Info("Handler HandleRestoreBackup");
            Console.WriteLine("HandleRestoreBackup triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleRestoreBackupAsync();
        }

        public static async Task HandleCreateProfile()
        {
            PortLogger.Info("Handler HandleCreateProfile");
            Console.WriteLine("HandleCreateProfile triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleCreateProfileAsync();
        }

        public static async Task HandleSwitchProfile(object data)
        {
            PortLogger.Info("Handler HandleSwitchProfile");
            Console.WriteLine("HandleSwitchProfile triggered");
            var profileName = ExtractProfileName(data);
            await ModManager.Backend.Ports.PortHandlers.HandleSwitchProfileAsync(profileName);
        }

        public static async Task HandleHeatmapCellClicked(object data)
        {
            PortLogger.Info("Handler HandleHeatmapCellClicked");
            Console.WriteLine("HandleHeatmapCellClicked triggered");
            var category = ExtractCategory(data);
            if (!string.IsNullOrWhiteSpace(category))
                await ModManager.Backend.Ports.PortHandlers.HandleCategoryFilterAsync(category);
            else
                await Task.CompletedTask;
        }

        // Existing backend ports (kept in contract IDs):

        public static async Task HandleEnableAllMods()
        {
            PortLogger.Info("Handler HandleEnableAllMods");
            Console.WriteLine("HandleEnableAllMods triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleEnableAllModsAsync();
        }

        public static async Task HandleDisableAllMods()
        {
            PortLogger.Info("Handler HandleDisableAllMods");
            Console.WriteLine("HandleDisableAllMods triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleDisableAllModsAsync();
        }

        public static async Task HandleDeleteProfile()
        {
            PortLogger.Info("Handler HandleDeleteProfile");
            Console.WriteLine("HandleDeleteProfile triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleDeleteProfileAsync();
        }

        public static async Task HandleDeployMods()
        {
            PortLogger.Info("Handler HandleDeployMods");
            Console.WriteLine("HandleDeployMods triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleDeployModsAsync();
        }

        public static async Task HandleOpenModsFolder()
        {
            PortLogger.Info("Handler HandleOpenModsFolder");
            Console.WriteLine("HandleOpenModsFolder triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleOpenModsFolderAsync();
        }

        public static async Task HandleSettings()
        {
            PortLogger.Info("Handler HandleSettings");
            Console.WriteLine("HandleSettings triggered");
            await ModManager.Backend.Ports.PortHandlers.HandleSettingsAsync();
        }

        public static async Task HandleExportJson(object data)
        {
            PortLogger.Info("Handler HandleExportJson");
            Console.WriteLine("HandleExportJson triggered");
            var outputPath = ExtractOutputPath(data);
            await ModManager.Backend.Ports.PortHandlers.HandleExportJsonAsync(outputPath);
        }

        public static async Task HandleModToggle(object data)
        {
            PortLogger.Info("Handler HandleModToggle");
            Console.WriteLine("HandleModToggle triggered");
            var payload = ExtractModToggle(data);
            await ModManager.Backend.Ports.PortHandlers.HandleModToggleAsync(payload.ModName, payload.Enabled);
        }

        public static async Task HandleModSelection(object data)
        {
            PortLogger.Info("Handler HandleModSelection");
            Console.WriteLine("HandleModSelection triggered");
            var modName = ExtractModName(data);
            await ModManager.Backend.Ports.PortHandlers.HandleModSelectionAsync(modName);
        }

        public static async Task HandleSearch(object data)
        {
            PortLogger.Info("Handler HandleSearch");
            Console.WriteLine("HandleSearch triggered");
            var text = ExtractText(data);
            await ModManager.Backend.Ports.PortHandlers.HandleSearchAsync(text);
        }

        public static async Task HandleCategoryFilter(object data)
        {
            PortLogger.Info("Handler HandleCategoryFilter");
            Console.WriteLine("HandleCategoryFilter triggered");
            var category = ExtractCategory(data);
            await ModManager.Backend.Ports.PortHandlers.HandleCategoryFilterAsync(category);
        }

        public static async Task HandleSortOrder(object data)
        {
            PortLogger.Info("Handler HandleSortOrder");
            Console.WriteLine("HandleSortOrder triggered");
            var orderType = ExtractOrderType(data);
            await ModManager.Backend.Ports.PortHandlers.HandleSortOrderAsync(orderType);
        }

        private static string ExtractText(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            // If payload is JSON, prefer known DTO shape.
            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.SearchPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.Text))
                        return dto.Text;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse SearchPayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static string ExtractModName(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.ModTogglePayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.ModName))
                        return dto.ModName;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse ModTogglePayload JSON (for mod name): {ex.GetType().Name}: {ex.Message}");
                }

                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.ModSelectionPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.ModName))
                        return dto.ModName;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse ModSelectionPayload JSON (for mod name): {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static PortContract.ModTogglePayload ExtractModToggle(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return new PortContract.ModTogglePayload();

            if (LooksLikeJson(s))
            {
                try
                {
                    return JsonSerializer.Deserialize<PortContract.ModTogglePayload>(s, _jsonOptions) ?? new PortContract.ModTogglePayload();
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse ModTogglePayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            // Fallback: plain string treated as mod name, enabled default true.
            return new PortContract.ModTogglePayload { ModName = s, Enabled = true };
        }

        private static string ExtractCategory(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.CategoryFilterPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.Category))
                        return dto.Category;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse CategoryFilterPayload JSON: {ex.GetType().Name}: {ex.Message}");
                }

                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.HeatmapCellClickedPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.Category))
                        return dto.Category;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse HeatmapCellClickedPayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static string ExtractOrderType(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.SortOrderPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.OrderType))
                        return dto.OrderType;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse SortOrderPayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static string ExtractProfileName(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.SwitchProfilePayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.ProfileName))
                        return dto.ProfileName;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse SwitchProfilePayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static string ExtractOutputPath(object data)
        {
            var s = data as string;
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;

            if (LooksLikeJson(s))
            {
                try
                {
                    var dto = JsonSerializer.Deserialize<PortContract.ExportJsonPayload>(s, _jsonOptions);
                    if (!string.IsNullOrWhiteSpace(dto?.OutputPath))
                        return dto.OutputPath;
                }
                catch (Exception ex)
                {
                    PortLogger.Warn($"Failed to parse ExportJsonPayload JSON: {ex.GetType().Name}: {ex.Message}");
                }
            }

            return s;
        }

        private static bool LooksLikeJson(string s)
        {
            s = s.Trim();
            return (s.StartsWith("{") && s.EndsWith("}")) || (s.StartsWith("[") && s.EndsWith("]"));
        }
    }
}
