using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace ModManagerPrototype
{
    public static class PortTestRunner
    {
        public static async Task RunTests()
        {
            Console.WriteLine("Running Port Tests...");

            // Ensure backend port handlers have a UI port, even when tests run before WinForms starts.
            ModManager.Backend.Ports.PortHandlers.Initialize(new TestUiPort());

            // No-payload ports
            await UIEventDispatcher.DispatchAsync(new PortData { Port = PortContract.PortIds.ScanMods });
            await UIEventDispatcher.DispatchAsync(new PortData { Port = PortContract.PortIds.RefreshMods });
            await UIEventDispatcher.DispatchAsync(new PortData { Port = PortContract.PortIds.GenerateLoadOrder });

            // Plain-string payload (back-compat)
            await UIEventDispatcher.DispatchAsync(new PortData { Port = PortContract.PortIds.EnableMod, Data = "TestMod" });

            // JSON payloads (preferred)
            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.ModToggle,
                Data = Json(new PortContract.ModTogglePayload { ModName = "JsonMod", Enabled = true })
            });

            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.SwitchProfile,
                Data = Json(new PortContract.SwitchProfilePayload { ProfileName = "Default" })
            });

            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.Search,
                Data = Json(new PortContract.SearchPayload { Text = "hud" })
            });

            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.CategoryFilter,
                Data = Json(new PortContract.CategoryFilterPayload { Category = "UI" })
            });

            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.SortOrder,
                Data = Json(new PortContract.SortOrderPayload { OrderType = "LoadOrder" })
            });

            // ExportJson: uses a safe temp path; will no-op if no mods scanned.
            var tempOut = Path.Combine(Path.GetTempPath(), "mods_load_order_test.json");
            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.ExportJson,
                Data = Json(new PortContract.ExportJsonPayload { OutputPath = tempOut })
            });

            // Direct snapshot port (no file IO): UI would receive via OnPortEmitted.
            await UIEventDispatcher.DispatchAsync(new PortData
            {
                Port = PortContract.PortIds.GetBackendSnapshot
            });

            Console.WriteLine("Port Tests Complete.");
        }

        private static string Json<T>(T payload)
            => JsonSerializer.Serialize(payload);

        private sealed class TestUiPort : ModManager.Backend.Ports.IUiPort
        {
            public string ModsPath => string.Empty;

            public void InvokeOnUi(Action action) => action();

            public void SetMods(System.Collections.Generic.IReadOnlyList<ModManager.Backend.Models.ModInfo> mods)
            {
                // no-op: test runner doesn't render UI
            }

            public void ShowInfo(string title, string message)
                => Console.WriteLine($"[UI INFO] {title}: {message}");

            public void ShowWarning(string title, string message)
                => Console.WriteLine($"[UI WARN] {title}: {message}");

            public void ShowError(string title, string message)
                => Console.WriteLine($"[UI ERROR] {title}: {message}");
        }
    }
}
