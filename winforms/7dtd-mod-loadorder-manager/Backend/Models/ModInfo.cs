using System.Collections.Generic;

namespace ModManager.Backend.Models
{
    public class ModInfo
    {
        // Stable identifier (prefer ModInfo.xml Id/ModId when available; else FolderName).
        public string Id { get; set; } = string.Empty;

        // Strong base fields (per your standard)
        public string Name { get; set; } = string.Empty;
        public bool Enabled { get; set; } = true;
        // Back-compat single category field (UI legacy). Prefer Categories.
        public string Category { get; set; } = string.Empty;
        public List<string> Categories { get; set; } = new List<string>();
        public string Status { get; set; } = string.Empty;

        // Declared dependencies (best-effort parsed from ModInfo.xml when present).
        public List<string> Dependencies { get; set; } = new List<string>();

        // Dependency diagnostics (computed at load-order time).
        public List<string> MissingDependencies { get; set; } = new();

        // Tiering hints (best-effort; populated by scanner + heuristics).
        public bool IsCoreFramework { get; set; }
        public bool IsOverhaul { get; set; }
        public bool IsUI { get; set; }
        public bool ContainsWorldGenFiles { get; set; }
        public bool ContainsPOIs { get; set; }
        public bool ContainsBiomes { get; set; }

        // UI-facing reasoning for why this mod was placed where it was.
        public string LoadReason { get; set; } = string.Empty;

        // Final resolved tier for display/binding.
        public ModTier ResolvedTier { get; set; } = ModTier.Content;

        // 0-100: heuristic confidence in tier/placement classification.
        public int PlacementConfidence { get; set; }

        // Conflict/impact diagnostics (computed by scanner + load-order engine).
        public bool HasConflict { get; set; }
        public int XPathOverlapCount { get; set; }
        public int LoadImpactScore { get; set; }

        // UI override ranking (optional; used as a deterministic tie-breaker).
        // Higher values load later within the same tier.
        public bool IsUiOverride { get; set; }
        public int UiOverrideRank { get; set; }

        // Best-effort list of XPath targets this mod attempts to touch.
        public List<string> XPathTargets { get; set; } = new();

        // Scan/load-order fields used by the current grid
        public int LoadOrder { get; set; } = 0;
        public string FolderName { get; set; } = string.Empty;
        public string ModRootPath { get; set; } = string.Empty;
        public bool HasModInfo { get; set; } = false;
        public string ModInfoPath { get; set; } = string.Empty;

        // Lightweight scan hints used by backend conflict heuristics.
        public bool HasDll { get; set; }
        public bool HasXml { get; set; }
        public bool UsesXpath { get; set; }

        public ModInfo DeepClone()
        {
            return new ModInfo
            {
                Id = Id,
                Name = Name,
                Enabled = Enabled,
                Category = Category,
                Categories = Categories != null ? new List<string>(Categories) : new List<string>(),
                Status = Status,
                Dependencies = Dependencies != null ? new List<string>(Dependencies) : new List<string>(),
                MissingDependencies = MissingDependencies != null ? new List<string>(MissingDependencies) : new List<string>(),
                IsCoreFramework = IsCoreFramework,
                IsOverhaul = IsOverhaul,
                IsUI = IsUI,
                ContainsWorldGenFiles = ContainsWorldGenFiles,
                ContainsPOIs = ContainsPOIs,
                ContainsBiomes = ContainsBiomes,
                LoadReason = LoadReason,
                ResolvedTier = ResolvedTier,
                PlacementConfidence = PlacementConfidence,
                HasConflict = HasConflict,
                XPathOverlapCount = XPathOverlapCount,
                LoadImpactScore = LoadImpactScore,
                IsUiOverride = IsUiOverride,
                UiOverrideRank = UiOverrideRank,
                XPathTargets = XPathTargets != null ? new List<string>(XPathTargets) : new List<string>(),
                LoadOrder = LoadOrder,
                FolderName = FolderName,
                ModRootPath = ModRootPath,
                HasModInfo = HasModInfo,
                ModInfoPath = ModInfoPath,
                HasDll = HasDll,
                HasXml = HasXml,
                UsesXpath = UsesXpath
            };
        }
    }
}
