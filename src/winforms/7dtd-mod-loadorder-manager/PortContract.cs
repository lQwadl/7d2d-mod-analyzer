using System;
using System.Collections.Generic;
using System.Threading.Tasks;

using ModManager.Backend.Models;

namespace ModManagerPrototype
{
    /// <summary>
    /// Shared UI ↔ Backend Port Contract.
    /// This file is the authority for port IDs.
    /// UI calls these ports; backend (VS Code project) implements handling.
    /// </summary>
    public static class PortContract
    {
        // Existing UI Event Ports (kept identical to the previously created values)
        public const int SELECT_FOLDER = 2001;
        public const int REFRESH_MODS = 2002;
        public const int ENABLE_MOD = 2003;
        public const int DISABLE_MOD = 2004;
        public const int MOVE_UP = 2005;
        public const int MOVE_DOWN = 2006;
        public const int OPTIMIZE_ORDER = 2007;
        public const int CREATE_BACKUP = 2008;
        public const int RESTORE_BACKUP = 2009;
        public const int CREATE_PROFILE = 2010;
        public const int LOAD_PROFILE = 2011;

        // New UI Event Ports (added for UI-only interaction triggers)
        public const int FORM_LOADED = 2012;
        public const int MOD_DOUBLE_CLICK = 2013;
        public const int MOD_LIST_KEYDOWN = 2014;

        // Top Action Bar Ports
        public const int SCAN_MODS = 2015;
        public const int GENERATE_APPLY_LOAD_ORDER = 2016;
        public const int EXPORT_LOAD_ORDER = 2017;
        public const int RENAME_FOLDER = 2018;
        public const int EXPLAIN_ISSUES = 2019;
        public const int RESOLVE_CONFLICTS = 2020;
        public const int FIND_DUPLICATES = 2021;
        public const int APPLY_UPDATE_FIXES = 2022;
        public const int EXPLAIN_SELECTED = 2023;
        public const int DIAGNOSE_VISIBILITY = 2024;

        // Filter / UI Control Ports
        public const int FILTER_CRITICAL = 2025;
        public const int FILTER_HIGH = 2026;
        public const int FILTER_LOW = 2027;
        public const int FILTER_REDUNDANT = 2028;
        public const int FILTER_DISABLED = 2029;
        public const int FILTER_OK = 2030;
        public const int FILTER_CATEGORY_CHANGED = 2031;
        public const int FILTER_SEVERITY_CHANGED = 2032;
        public const int FILTER_CONFLICTS_ONLY_CHANGED = 2033;
        public const int FILTER_SHOW_ALL_CHANGED = 2034;

        // Heatmap Ports
        public const int HEATMAP_CELL_CLICKED = 2035;

        // Mods Search
        public const int FILTER_SEARCH_TEXT_CHANGED = 2036;

        /// <summary>
        /// Canonical IDs used by the backend dispatcher.
        /// These are aliases over the existing PortContract constants where possible.
        /// </summary>
        public static class PortIds
        {
            public const int ScanMods = SCAN_MODS;
            public const int RefreshMods = REFRESH_MODS;
            public const int GenerateLoadOrder = GENERATE_APPLY_LOAD_ORDER;

            public const int CheckConflicts = EXPLAIN_ISSUES;
            public const int ResolveConflicts = RESOLVE_CONFLICTS;

            public const int CreateBackup = CREATE_BACKUP;
            public const int RestoreBackup = RESTORE_BACKUP;

            public const int CreateProfile = CREATE_PROFILE;
            public const int SwitchProfile = LOAD_PROFILE;

            public const int EnableMod = ENABLE_MOD;
            public const int DisableMod = DISABLE_MOD;

            public const int ModSelection = MOD_DOUBLE_CLICK;
            public const int Search = FILTER_SEARCH_TEXT_CHANGED;
            public const int CategoryFilter = FILTER_CATEGORY_CHANGED;
            public const int HeatmapCellClicked = HEATMAP_CELL_CLICKED;

            // Backend-only / not yet wired in the UI
            public const int EnableAllMods = 2101;
            public const int DisableAllMods = 2102;
            public const int DeleteProfile = 2103;
            public const int DeployMods = 2104;
            public const int OpenModsFolder = 2105;
            public const int Settings = 2106;
            public const int ExportJson = EXPORT_LOAD_ORDER;
            public const int ModToggle = 2107;
            public const int SortOrder = 2108;

            // Backend -> UI
            public const int GetBackendSnapshot = 9001;
        }

        /// <summary>
        /// Backend-facing dispatcher interface.
        /// Implementations map PortIds -> handler methods.
        /// </summary>
        public interface IPortDispatcher
        {
            Task DispatchAsync(int portId, string payloadJson);
        }

        public sealed class SwitchProfilePayload
        {
            public string? ProfileName { get; set; }
        }

        public sealed class ExportJsonPayload
        {
            public string? OutputPath { get; set; }
        }

        public sealed class ModTogglePayload
        {
            public string? ModName { get; set; }
            public bool Enabled { get; set; }
        }

        public sealed class ModSelectionPayload
        {
            public string? ModName { get; set; }
        }

        public sealed class SearchPayload
        {
            public string? Text { get; set; }
        }

        public sealed class CategoryFilterPayload
        {
            public string? Category { get; set; }
        }

        public sealed class SortOrderPayload
        {
            public string? OrderType { get; set; }
        }

        public sealed class HeatmapCellClickedPayload
        {
            public string? Category { get; set; }
        }
    }

    /// <summary>
    /// Port payload sent from UI to backend.
    /// </summary>
    public class PortData
    {
        public int Port { get; set; }
        public object? Data { get; set; }
    }

    /// <summary>
    /// Backend handler interface (implemented by the VS Code project).
    /// </summary>
    public interface IUIEventHandler
    {
        void HandleUIEvent(PortData eventData);
    }

    /// <summary>
    /// Backend-provided snapshot for UI rendering.
    /// UI must treat this data as authoritative and render only.
    /// </summary>
    public class BackendSnapshot
    {
        public int SchemaVersion { get; set; } = 1;

        public List<CategorySnapshot> Categories { get; set; } = new List<CategorySnapshot>();
        public TotalsSnapshot Totals { get; set; } = new TotalsSnapshot();
        public MetaSnapshot Meta { get; set; } = new MetaSnapshot();
        public ErrorSnapshot? Error { get; set; }

        // Optional: per-mod details for the mods grid.
        public List<ModInfo>? Mods { get; set; }
    }

    public class CategorySnapshot
    {
        public string Category { get; set; } = string.Empty;
        public int TotalMods { get; set; }
        public Dictionary<string, int> Severity { get; set; } = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, double> Percentages { get; set; } = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
    }

    public class TotalsSnapshot
    {
        public int Mods { get; set; }
        public int Enabled { get; set; }
        public int Disabled { get; set; }
        public int Conflicts { get; set; }
    }

    public class MetaSnapshot
    {
        public string GeneratedAt { get; set; } = string.Empty;
        public int ScanDurationMs { get; set; }
    }

    public class ErrorSnapshot
    {
        public string Code { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
        public string Details { get; set; } = string.Empty;
    }
}
