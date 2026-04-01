using System;
using System.Text.Json;
using System.Threading.Tasks;
using ModManager.Backend.Services;
using ModManagerPrototype;

namespace ModManager.Backend.Ports
{
    /// <summary>
    /// ID-based port dispatcher.
    ///
    /// UI should call DispatchAsync(portId, payloadJson).
    /// Backend maps portId -> PortHandlers method.
    /// </summary>
    public sealed class PortDispatcher : PortContract.IPortDispatcher
    {
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };

        public async Task DispatchAsync(int portId, string payloadJson)
        {
            PortLogger.Info($"DispatchStart portId={portId}");

            try
            {
                switch (portId)
                {
                    case PortContract.PortIds.ScanMods:
                        await PortHandlers.HandleScanModsAsync();
                        return;

                    case PortContract.PortIds.RefreshMods:
                        await PortHandlers.HandleRefreshModsAsync();
                        return;

                    case PortContract.PortIds.GenerateLoadOrder:
                        await PortHandlers.HandleGenerateLoadOrderAsync();
                        return;

                    case PortContract.PortIds.CheckConflicts:
                        await PortHandlers.HandleConflictScanAsync();
                        return;

                    case PortContract.PortIds.ResolveConflicts:
                        await PortHandlers.HandleResolveConflictsAsync();
                        return;

                    case PortContract.PortIds.CreateBackup:
                        await PortHandlers.HandleBackupModsAsync();
                        return;

                    case PortContract.PortIds.RestoreBackup:
                        await PortHandlers.HandleRestoreBackupAsync();
                        return;

                    case PortContract.PortIds.CreateProfile:
                        await PortHandlers.HandleCreateProfileAsync();
                        return;

                    case PortContract.PortIds.SwitchProfile:
                        {
                            var payload = DeserializeOrDefault<PortContract.SwitchProfilePayload>(payloadJson);
                            await PortHandlers.HandleSwitchProfileAsync(payload.ProfileName ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.EnableAllMods:
                        await PortHandlers.HandleEnableAllModsAsync();
                        return;

                    case PortContract.PortIds.DisableAllMods:
                        await PortHandlers.HandleDisableAllModsAsync();
                        return;

                    case PortContract.PortIds.DeleteProfile:
                        await PortHandlers.HandleDeleteProfileAsync();
                        return;

                    case PortContract.PortIds.DeployMods:
                        await PortHandlers.HandleDeployModsAsync();
                        return;

                    case PortContract.PortIds.OpenModsFolder:
                        await PortHandlers.HandleOpenModsFolderAsync();
                        return;

                    case PortContract.PortIds.Settings:
                        await PortHandlers.HandleSettingsAsync();
                        return;

                    case PortContract.PortIds.ExportJson:
                        {
                            var payload = DeserializeOrDefault<PortContract.ExportJsonPayload>(payloadJson);
                            await PortHandlers.HandleExportJsonAsync(payload.OutputPath ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.EnableMod:
                        {
                            var payload = DeserializeOrDefault<PortContract.ModTogglePayload>(payloadJson);
                            await PortHandlers.HandleModToggleAsync(payload.ModName ?? string.Empty, true);
                            return;
                        }

                    case PortContract.PortIds.DisableMod:
                        {
                            var payload = DeserializeOrDefault<PortContract.ModTogglePayload>(payloadJson);
                            await PortHandlers.HandleModToggleAsync(payload.ModName ?? string.Empty, false);
                            return;
                        }

                    case PortContract.PortIds.ModToggle:
                        {
                            var payload = DeserializeOrDefault<PortContract.ModTogglePayload>(payloadJson);
                            await PortHandlers.HandleModToggleAsync(payload.ModName ?? string.Empty, payload.Enabled);
                            return;
                        }

                    case PortContract.PortIds.ModSelection:
                        {
                            var payload = DeserializeOrDefault<PortContract.ModSelectionPayload>(payloadJson);
                            await PortHandlers.HandleModSelectionAsync(payload.ModName ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.Search:
                        {
                            var payload = DeserializeOrDefault<PortContract.SearchPayload>(payloadJson);
                            await PortHandlers.HandleSearchAsync(payload.Text ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.CategoryFilter:
                        {
                            var payload = DeserializeOrDefault<PortContract.CategoryFilterPayload>(payloadJson);
                            await PortHandlers.HandleCategoryFilterAsync(payload.Category ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.SortOrder:
                        {
                            var payload = DeserializeOrDefault<PortContract.SortOrderPayload>(payloadJson);
                            await PortHandlers.HandleSortOrderAsync(payload.OrderType ?? string.Empty);
                            return;
                        }

                    case PortContract.PortIds.HeatmapCellClicked:
                        {
                            // Minimal default behavior: treat heatmap click as a category filter.
                            // UI can evolve payload details without changing this dispatch signature.
                            var payload = DeserializeOrDefault<PortContract.HeatmapCellClickedPayload>(payloadJson);
                            if (!string.IsNullOrWhiteSpace(payload.Category))
                                await PortHandlers.HandleCategoryFilterAsync(payload.Category);
                            return;
                        }

                    case PortContract.PortIds.GetBackendSnapshot:
                        await PortHandlers.HandleGetBackendSnapshotAsync();
                        return;

                    default:
                        PortLogger.Warn($"DispatchUnknown portId={portId}");
                        return;
                }
            }
            catch (Exception ex)
            {
                PortLogger.Error($"DispatchFail portId={portId}", ex);

                // Don't throw unless you want UI to crash; PortHandlers already surfaces errors.
                // Keeping dispatcher resilient is usually preferred.
                return;
            }
            finally
            {
                PortLogger.Info($"DispatchEnd portId={portId}");
            }
        }

        private static T DeserializeOrDefault<T>(string payloadJson) where T : new()
        {
            if (string.IsNullOrWhiteSpace(payloadJson))
                return new T();

            try
            {
                var value = JsonSerializer.Deserialize<T>(payloadJson, _jsonOptions);
                return value ?? new T();
            }
            catch
            {
                return new T();
            }
        }
    }
}
