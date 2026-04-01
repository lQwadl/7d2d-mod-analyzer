using System;
using System.Diagnostics;
using System.Text.Json;
using System.Threading.Tasks;
using ModManager.Backend.Services;
using ModManager.Backend.Ports;

namespace ModManagerPrototype
{
    /// <summary>
    /// UI -> Backend dispatch entrypoint.
    ///
    /// Windsurf/UI sends Port IDs + optional payload; VS Code backend maps to handlers.
    /// No UI control references allowed.
    /// </summary>
    public static class UIEventDispatcher
    {
        private static readonly PortDispatcher _dispatcher = new PortDispatcher();

        // UI-facing method some systems expect.
        public static async Task HandleUIEvent(PortData e) => await DispatchAsync(e);

        public static async Task DispatchAsync(PortData data)
        {
            if (data is null)
                return;

            var portId = data.Port;
            var payload = BuildPayloadJson(portId, data.Data);

            // Adapter: UI -> PortDispatcher (single mapping source of truth).
            await ExecutePortAsync(portId, payload, () => _dispatcher.DispatchAsync(portId, payload));
        }

        private static string BuildPayloadJson(int portId, object? data)
        {
            if (data is null)
                return string.Empty;

            if (data is string s)
            {
                // If caller already provided JSON, pass through.
                var trimmed = s.Trim();
                if ((trimmed.StartsWith("{") && trimmed.EndsWith("}")) || (trimmed.StartsWith("[") && trimmed.EndsWith("]")))
                    return s;

                // Back-compat: many UI call sites pass raw strings. Wrap into expected payload shapes.
                switch (portId)
                {
                    case PortContract.PortIds.Search:
                        return JsonSerializer.Serialize(new PortContract.SearchPayload { Text = s });

                    case PortContract.PortIds.CategoryFilter:
                        return JsonSerializer.Serialize(new PortContract.CategoryFilterPayload { Category = s });

                    case PortContract.PortIds.SortOrder:
                        return JsonSerializer.Serialize(new PortContract.SortOrderPayload { OrderType = s });

                    case PortContract.PortIds.HeatmapCellClicked:
                        return JsonSerializer.Serialize(new PortContract.HeatmapCellClickedPayload { Category = s });

                    case PortContract.PortIds.SwitchProfile:
                        return JsonSerializer.Serialize(new PortContract.SwitchProfilePayload { ProfileName = s });

                    case PortContract.PortIds.ModSelection:
                        return JsonSerializer.Serialize(new PortContract.ModSelectionPayload { ModName = s });

                    case PortContract.PortIds.ModToggle:
                        return JsonSerializer.Serialize(new PortContract.ModTogglePayload { ModName = s, Enabled = true });

                    case PortContract.PortIds.EnableMod:
                        return JsonSerializer.Serialize(new PortContract.ModTogglePayload { ModName = s, Enabled = true });

                    case PortContract.PortIds.DisableMod:
                        return JsonSerializer.Serialize(new PortContract.ModTogglePayload { ModName = s, Enabled = false });

                    default:
                        return s;
                }
            }

            // If caller passed a payload object, serialize it.
            try
            {
                return JsonSerializer.Serialize(data);
            }
            catch
            {
                return string.Empty;
            }
        }

        private static async Task ExecutePortAsync(int portId, string payload, Func<Task> action)
        {
            var sw = Stopwatch.StartNew();
            PortLogger.Info($"PortStart portId={portId}");
            Console.WriteLine($"[PORT START] {portId}");

            try
            {
                await action();
                PortLogger.Info($"PortEnd portId={portId} durationMs={sw.ElapsedMilliseconds}");
                Console.WriteLine($"[PORT END] {portId} ({sw.ElapsedMilliseconds}ms)");
            }
            catch (Exception ex)
            {
                PortLogger.Error($"PortFail portId={portId} durationMs={sw.ElapsedMilliseconds}", ex);
                Console.WriteLine($"[PORT ERROR] {portId} {ex.Message}");
            }
        }
    }
}
