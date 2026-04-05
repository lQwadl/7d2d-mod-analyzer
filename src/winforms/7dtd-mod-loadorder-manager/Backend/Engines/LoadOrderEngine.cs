using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    public class LoadOrderEngine
    {
        public Task<IReadOnlyList<ModInfo>> GenerateAsync(IReadOnlyList<ModInfo> mods)
        {
            return Task.Run<IReadOnlyList<ModInfo>>(() =>
            {
                var input = mods ?? Array.Empty<ModInfo>();

                // Clone input to keep the backend's snapshot model stable.
                var all = input
                    .OrderBy(m => m.FolderName, StringComparer.OrdinalIgnoreCase)
                    .Select(Clone)
                    .ToList();

                // Split enabled vs disabled; disabled mods always come after enabled in the final list.
                var enabled = all.Where(m => m.Enabled).ToList();
                var disabled = all.Where(m => !m.Enabled).ToList();

                // Preflight diagnostics (for UI): missing deps + XPath overlap conflicts.
                DetectMissingDependencies(all);
                DetectXPathConflicts(all);

                var orderedEnabled = SortByDependenciesAndTier(enabled);
                var orderedDisabled = disabled
                    .Select(m =>
                    {
                        var resolved = ResolveTier(m);
                        return (Mod: m, Tier: resolved.Tier);
                    })
                    .OrderBy(x => GetTierOrder(x.Tier))
                    .ThenBy(x => GetNumericPrefix(x.Mod))
                    .ThenBy(x => GetContentGroupBias(x.Mod))
                    .ThenBy(x => GetConflictBias(x.Mod))
                    .ThenBy(x => GetUiOverrideRank(x.Mod))
                    .ThenBy(x => GetDeterministicName(x.Mod), StringComparer.OrdinalIgnoreCase)
                    .ThenBy(x => x.Mod.FolderName ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                    .ThenBy(x => x.Mod.Id ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                    .Select(x => x.Mod)
                    .ToList();

                var ordered = new List<ModInfo>(orderedEnabled.Count + orderedDisabled.Count);
                ordered.AddRange(orderedEnabled);
                ordered.AddRange(orderedDisabled);

                var order = 1;
                foreach (var m in ordered)
                    m.LoadOrder = order++;

                return ordered;
            });
        }

        private static ModInfo Clone(ModInfo m)
        {
            return new ModInfo
            {
                Id = m.Id,
                Name = m.Name,
                Enabled = m.Enabled,
                Category = m.Category,
                Categories = m.Categories?.ToList() ?? new List<string>(),
                Status = m.Status,
                Dependencies = m.Dependencies?.ToList() ?? new List<string>(),
                MissingDependencies = m.MissingDependencies?.ToList() ?? new List<string>(),
                IsCoreFramework = m.IsCoreFramework,
                IsOverhaul = m.IsOverhaul,
                IsUI = m.IsUI,
                ContainsWorldGenFiles = m.ContainsWorldGenFiles,
                ContainsPOIs = m.ContainsPOIs,
                ContainsBiomes = m.ContainsBiomes,
                LoadReason = m.LoadReason,
                ResolvedTier = m.ResolvedTier,
                PlacementConfidence = m.PlacementConfidence,
                HasConflict = m.HasConflict,
                XPathOverlapCount = m.XPathOverlapCount,
                LoadImpactScore = m.LoadImpactScore,
                IsUiOverride = m.IsUiOverride,
                UiOverrideRank = m.UiOverrideRank,
                XPathTargets = m.XPathTargets?.ToList() ?? new List<string>(),
                FolderName = m.FolderName,
                ModRootPath = m.ModRootPath,
                HasModInfo = m.HasModInfo,
                ModInfoPath = m.ModInfoPath,
                LoadOrder = m.LoadOrder,
                HasDll = m.HasDll,
                HasXml = m.HasXml,
                UsesXpath = m.UsesXpath,
            };
        }

        private static void DetectMissingDependencies(List<ModInfo> mods)
        {
            mods ??= new List<ModInfo>();

            var keyToIds = BuildDependencyKeyIndex(mods);
            var ids = mods
                .Select(m => (m.Id ?? string.Empty).Trim())
                .Where(x => x.Length > 0)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            foreach (var mod in mods)
            {
                mod.MissingDependencies ??= new List<string>();
                mod.MissingDependencies.Clear();

                if (mod.Dependencies == null || mod.Dependencies.Count == 0)
                    continue;

                foreach (var depRaw in mod.Dependencies)
                {
                    if (string.IsNullOrWhiteSpace(depRaw))
                        continue;

                    var depId = ResolveDependencyId(depRaw, keyToIds);

                    // If it can't be resolved to any known mod id/name/folder, treat it as missing.
                    if (string.IsNullOrWhiteSpace(depId))
                    {
                        var token = depRaw.Trim();
                        if (!mod.MissingDependencies.Contains(token))
                            mod.MissingDependencies.Add(token);
                        continue;
                    }

                    // If it resolves, but the id still isn't present (should be rare), mark missing by id.
                    if (!ids.Contains(depId) && !mod.MissingDependencies.Contains(depId))
                        mod.MissingDependencies.Add(depId);
                }
            }
        }

        private static void DetectXPathConflicts(List<ModInfo> mods)
        {
            mods ??= new List<ModInfo>();

            foreach (var mod in mods)
            {
                mod.HasConflict = false;
                mod.XPathOverlapCount = 0;
            }

            var targetMap = new Dictionary<string, List<ModInfo>>(StringComparer.OrdinalIgnoreCase);

            foreach (var mod in mods.Where(m => m.UsesXpath))
            {
                if (mod.XPathTargets == null || mod.XPathTargets.Count == 0)
                    continue;

                foreach (var target in mod.XPathTargets)
                {
                    var key = (target ?? string.Empty).Trim();
                    if (key.Length == 0)
                        continue;

                    if (!targetMap.TryGetValue(key, out var list))
                    {
                        list = new List<ModInfo>();
                        targetMap[key] = list;
                    }

                    list.Add(mod);
                }
            }

            foreach (var kvp in targetMap)
            {
                if (kvp.Value.Count <= 1)
                    continue;

                foreach (var mod in kvp.Value)
                {
                    mod.HasConflict = true;
                    mod.XPathOverlapCount++;
                }
            }
        }

        private static List<ModInfo> SortByDependenciesAndTier(List<ModInfo> mods)
        {
            // Kahn topological sort with deterministic priority selection among available nodes.
            // This guarantees: dependencies first, stable results, tier ordering where it doesn't violate dependencies.
            mods ??= new List<ModInfo>();
            if (mods.Count <= 1)
                return mods.ToList();

            foreach (var m in mods)
            {
                if (string.IsNullOrWhiteSpace(m.Id))
                    m.Id = !string.IsNullOrWhiteSpace(m.FolderName) ? m.FolderName : (m.Name ?? string.Empty);
            }

            var idToMod = mods
                .GroupBy(m => m.Id.Trim(), StringComparer.OrdinalIgnoreCase)
                .ToDictionary(g => g.Key, g => g.OrderBy(x => x.FolderName, StringComparer.OrdinalIgnoreCase).First(), StringComparer.OrdinalIgnoreCase);

            // Resolve tier + base reason once per mod (avoid mutating within comparers).
            var tierById = new Dictionary<string, ModTier>(StringComparer.OrdinalIgnoreCase);
            var baseReasonById = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var kvp in idToMod)
            {
                var resolved = ResolveTier(kvp.Value);
                tierById[kvp.Key] = resolved.Tier;
                baseReasonById[kvp.Key] = resolved.Reason;
            }

            var keyToIds = BuildDependencyKeyIndex(mods);

            var prereqs = new Dictionary<string, HashSet<string>>(StringComparer.OrdinalIgnoreCase);
            var outgoing = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
            var inDegree = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

            foreach (var mod in mods)
            {
                var id = mod.Id.Trim();
                prereqs[id] = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                outgoing[id] = new List<string>();
                inDegree[id] = 0;
            }

            foreach (var mod in mods)
            {
                var id = mod.Id.Trim();

                foreach (var depRaw in (mod.Dependencies ?? new List<string>()))
                {
                    var depId = ResolveDependencyId(depRaw, keyToIds);
                    if (string.IsNullOrWhiteSpace(depId))
                        continue;

                    if (string.Equals(depId, id, StringComparison.OrdinalIgnoreCase))
                        continue;

                    // Only consider dependencies that are part of this enabled set.
                    if (!idToMod.ContainsKey(depId))
                        continue;

                    if (prereqs[id].Add(depId))
                    {
                        outgoing[depId].Add(id);
                        inDegree[id] = inDegree[id] + 1;
                    }
                }
            }

            var comparer = Comparer<string>.Create((a, b) => CompareByPriority(idToMod[a], tierById[a], idToMod[b], tierById[b]));
            var available = new SortedSet<string>(comparer);
            var remaining = new HashSet<string>(idToMod.Keys, StringComparer.OrdinalIgnoreCase);

            foreach (var kvp in inDegree)
            {
                if (kvp.Value == 0)
                    available.Add(kvp.Key);
            }

            var result = new List<ModInfo>(mods.Count);
            var cycleBreaks = 0;

            while (remaining.Count > 0)
            {
                string next;
                if (available.Count > 0)
                {
                    next = available.Min!;
                    available.Remove(next);
                }
                else
                {
                    // Cycle (or only unresolved prereqs). Break deterministically by picking the best remaining node.
                    next = remaining
                        .OrderBy(id => GetTierOrder(tierById[id]))
                        .ThenBy(id => GetNumericPrefix(idToMod[id]))
                        .ThenBy(id => GetContentGroupBias(idToMod[id]))
                        .ThenBy(id => GetConflictBias(idToMod[id]))
                        .ThenBy(id => GetUiOverrideRank(idToMod[id]))
                        .ThenBy(id => GetDeterministicName(idToMod[id]), StringComparer.OrdinalIgnoreCase)
                        .ThenBy(id => idToMod[id].FolderName ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                        .ThenBy(id => idToMod[id].Id ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                        .First();
                    cycleBreaks++;

                    // Surface this to the UI as a reason.
                    baseReasonById[next] = (baseReasonById.TryGetValue(next, out var r) ? r : string.Empty) + " Circular dependency detected in set — deterministic fallback ordering.";
                }

                if (!remaining.Remove(next))
                    continue;

                result.Add(idToMod[next]);

                // "Remove" next from graph.
                foreach (var child in outgoing[next])
                {
                    if (!remaining.Contains(child))
                        continue;

                    inDegree[child] = Math.Max(0, inDegree[child] - 1);
                    if (inDegree[child] == 0)
                        available.Add(child);
                }
            }

            if (cycleBreaks > 0)
                Trace.WriteLine($"[LoadOrder] Cycle(s) detected; broke {cycleBreaks} time(s) with deterministic fallback.");

            // Assign reasons + dependency placement notes.
            foreach (var mod in result)
            {
                var id = (mod.Id ?? string.Empty).Trim();
                if (id.Length == 0)
                    continue;

                if (baseReasonById.TryGetValue(id, out var reason))
                    mod.LoadReason = reason;

                if (prereqs.TryGetValue(id, out var deps) && deps.Count > 0)
                {
                    // Dependencies were resolved to in-set ids and placed earlier, so we can be slightly more confident.
                    mod.PlacementConfidence = Math.Min(mod.PlacementConfidence + 5, 100);

                    var depNames = deps
                        .Where(d => idToMod.ContainsKey(d))
                        .Select(d => GetDeterministicName(idToMod[d]))
                        .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
                        .ToList();

                    if (depNames.Count > 0)
                        mod.LoadReason += $" Loaded after dependencies: {string.Join(", ", depNames)}.";

                    var coreDeps = deps.Where(d => tierById.TryGetValue(d, out var t) && t == ModTier.Core)
                        .Select(d => GetDeterministicName(idToMod[d]))
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
                        .ToList();

                    if (coreDeps.Count > 0)
                        mod.LoadReason += $" Depends on core framework(s): {string.Join(", ", coreDeps)}.";
                }

                mod.LoadReason = (mod.LoadReason ?? string.Empty).Trim();
            }

            return result;
        }

        private static Dictionary<string, List<string>> BuildDependencyKeyIndex(List<ModInfo> mods)
        {
            var index = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
            void AddKey(string key, string id)
            {
                if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(id))
                    return;

                if (!index.TryGetValue(key, out var list))
                {
                    list = new List<string>();
                    index[key] = list;
                }

                if (!list.Contains(id, StringComparer.OrdinalIgnoreCase))
                    list.Add(id);
            }

            foreach (var mod in mods)
            {
                var id = (mod.Id ?? string.Empty).Trim();
                if (string.IsNullOrWhiteSpace(id))
                    continue;

                AddKey(NormalizeKey(mod.Id), id);
                AddKey(NormalizeKey(mod.FolderName), id);
                AddKey(NormalizeKey(mod.Name), id);
            }

            return index;
        }

        private static string NormalizeKey(string? s)
        {
            if (string.IsNullOrWhiteSpace(s))
                return string.Empty;
            return s.Trim();
        }

        private static string ResolveDependencyId(string depRaw, Dictionary<string, List<string>> keyToIds)
        {
            var key = NormalizeKey(depRaw);
            if (string.IsNullOrWhiteSpace(key))
                return string.Empty;

            if (!keyToIds.TryGetValue(key, out var ids))
                return string.Empty;

            if (ids.Count == 1)
                return ids[0];

            // Ambiguous dependency reference (e.g., multiple mods share the same Name). Ignore rather than guess.
            return string.Empty;
        }

        private static int CompareByPriority(ModInfo a, ModTier aTier, ModInfo b, ModTier bTier)
        {
            var c = GetTierOrder(aTier).CompareTo(GetTierOrder(bTier));
            if (c != 0) return c;

            c = GetNumericPrefix(a).CompareTo(GetNumericPrefix(b));
            if (c != 0) return c;

            c = GetContentGroupBias(a).CompareTo(GetContentGroupBias(b));
            if (c != 0) return c;

            c = GetConflictBias(a).CompareTo(GetConflictBias(b));
            if (c != 0) return c;

            c = GetUiOverrideRank(a).CompareTo(GetUiOverrideRank(b));
            if (c != 0) return c;

            c = StringComparer.OrdinalIgnoreCase.Compare(GetDeterministicName(a), GetDeterministicName(b));
            if (c != 0) return c;

            c = StringComparer.OrdinalIgnoreCase.Compare(a.FolderName ?? string.Empty, b.FolderName ?? string.Empty);
            if (c != 0) return c;

            return StringComparer.OrdinalIgnoreCase.Compare(a.Id ?? string.Empty, b.Id ?? string.Empty);
        }

        private static int GetTierOrder(ModTier tier)
        {
            // High-level order (override semantics):
            // Core -> Library/Utilities (incl UI frameworks) -> Overhaul/Gameplay -> Content -> WorldGen -> UI overrides -> Patch
            // Rationale: HUD/XUI mods often need to be late to avoid being overwritten.
            // Patches always last.
            return tier switch
            {
                ModTier.Core => 0,
                ModTier.Library => 1,
                ModTier.Overhaul => 2,
                ModTier.Content => 3,
                ModTier.WorldGen => 4,
                ModTier.UI => 5,
                ModTier.Patch => 6,
                _ => 99
            };
        }

        private static int GetNumericPrefix(ModInfo mod)
        {
            // Respect explicit numeric prefix patterns like:
            // 0640_ModName, 0640-ModName, 0640 ModName
            // Smaller numbers load earlier within the same tier.
            var folder = (mod.FolderName ?? string.Empty).Trim();
            if (folder.Length == 0)
                return int.MaxValue;

            var i = 0;
            while (i < folder.Length && char.IsDigit(folder[i]))
                i++;

            if (i <= 0)
                return int.MaxValue;

            if (int.TryParse(folder.Substring(0, i), out var n))
                return n;

            return int.MaxValue;
        }

        private static int GetContentGroupBias(ModInfo mod)
        {
            // Only used as a tie-breaker inside the same tier.
            // Lower = earlier.
            var category = (mod.Category ?? string.Empty).Trim();
            var categories = mod.Categories ?? new List<string>();
            var catText = string.Join(" ", new[] { category }.Concat(categories)).ToLowerInvariant();

            // Cosmetics last.
            if (catText.Contains("visual") || catText.Contains("audio") || catText.Contains("texture") || catText.Contains("sound") || catText.Contains("cosmetic") || catText.Contains("decor"))
                return 30;

            // Environment/biomes/pois later than weapons.
            if (catText.Contains("biome") || catText.Contains("weather") || catText.Contains("environment") || catText.Contains("poi") || catText.Contains("prefab"))
                return 20;

            // Weapons/combat.
            if (catText.Contains("weapon") || catText.Contains("gun") || catText.Contains("combat") || catText.Contains("melee"))
                return 10;

            // Gameplay mechanics (default earlier within content).
            if (catText.Contains("gameplay") || catText.Contains("craft") || catText.Contains("survival") || catText.Contains("loot") || catText.Contains("quest"))
                return 0;

            return 5;
        }

        private static string GetDeterministicName(ModInfo mod)
        {
            if (!string.IsNullOrWhiteSpace(mod.Name))
                return mod.Name.Trim();
            if (!string.IsNullOrWhiteSpace(mod.FolderName))
                return mod.FolderName.Trim();
            return mod.Id?.Trim() ?? string.Empty;
        }

        private static int GetConflictBias(ModInfo mod)
        {
            // Higher = later within the same tier (helps keep "more overriding" mods later).
            var bias = 0;
            if (mod.HasXml) bias += 10;
            if (mod.UsesXpath) bias += 100;
            return bias;
        }

        private static int GetUiOverrideRank(ModInfo mod)
        {
            // Lower = earlier, higher = later.
            // Only apply inside UI tier; other tiers return 0 for stability.
            if (mod == null) return 0;
            if (mod.ResolvedTier != ModTier.UI) return 0;

            if (mod.UiOverrideRank != 0)
                return mod.UiOverrideRank;

            // If flagged but no explicit rank, still bias later deterministically.
            return mod.IsUiOverride ? 50 : 0;
        }

        private static (ModTier Tier, string Reason) ResolveTier(ModInfo mod)
        {
            // Context-aware tier mapping + UI-facing reasoning.
            // NOTE: this intentionally does NOT trust mod.Category blindly.

            var category = (mod.Category ?? string.Empty).Trim();
            var categories = mod.Categories ?? new List<string>();
            var catText = string.Join(" ", new[] { category }.Concat(categories)).ToLowerInvariant();

            var nameText = string.Join(" ", new[] { mod.Name, mod.FolderName, mod.Id })
                .ToLowerInvariant();

            // Reset per-run hints so repeated ordering remains deterministic.
            mod.IsUiOverride = false;
            mod.UiOverrideRank = 0;

            var confidence = 50;
            (ModTier tier, string reason) resolved;

            // Hard override
            if (mod.IsCoreFramework
                || category.Equals("Core", StringComparison.OrdinalIgnoreCase)
                || nameText.Contains("_core")
                || nameText.StartsWith("core ")
                || nameText.StartsWith("core_")
                || nameText.StartsWith("core-")
                || nameText.StartsWith("0-")
                || nameText.StartsWith("00-"))
            {
                resolved = (ModTier.Core, "Core framework detected.");
                confidence = 95;
            }
            else if (nameText.Contains("hud") || nameText.Contains("xui") || nameText.Contains("uiframework") || nameText.Contains("ui framework") || nameText.Contains("smx") || nameText.Contains("ocb"))
            {
                // Explicit HUD/UI keyword heuristics.
                // If it looks like a framework (or ships a DLL), treat as dependency/library.
                // Otherwise, if it ships XML/XPath, treat as late UI override.
                var looksLikeFramework = nameText.Contains("framework") || nameText.Contains("uiframework") || nameText.Contains("api") || nameText.Contains("library");

                if (looksLikeFramework || mod.HasDll)
                {
                    resolved = (ModTier.Library, "HUD/XUI framework keyword detected — treated as Library/Dependency.");
                    confidence = 88;
                }
                else if (mod.HasXml || mod.UsesXpath)
                {
                    mod.IsUiOverride = true;
                    mod.UiOverrideRank = 80;
                    resolved = (ModTier.UI, "HUD/XUI keyword + XML/XPath detected — treated as UI override (loads late).");
                    confidence = 86;
                }
                else
                {
                    resolved = (ModTier.UI, "HUD/XUI keyword detected — treated as UI (loads late).");
                    confidence = 75;
                }
            }
            else if ((catText.Contains("ui") || catText.Contains("hud") || nameText.Contains("ui") || nameText.Contains("hud"))
                && (catText.Contains("framework") || nameText.Contains("framework")))
            {
                resolved = (ModTier.Library, "UI framework detected — treated as Library/Dependency.");
                confidence = 88;
            }
            else if (catText.Contains("tool") || catText.Contains("utility") || nameText.Contains("servertools") || nameText.Contains("server tools"))
            {
                resolved = (ModTier.Library, "Utility/tooling mod detected — treated as Library/Utility.");
                confidence = 75;
            }
            else if (nameText.Contains("hemsoft") && (mod.HasXml || mod.UsesXpath))
            {
                mod.IsUiOverride = true;
                mod.UiOverrideRank = Math.Max(mod.UiOverrideRank, 90);
                resolved = (ModTier.UI, "HemSoft QoL detected — treated as UI override (loads late).");
                confidence = 78;
            }
            else if (mod.HasDll && !mod.UsesXpath)
            {
                resolved = (ModTier.Library, "Contains DLL — treated as Library.");
                confidence = 90;
            }
            else if (mod.IsOverhaul || catText.Contains("overhaul"))
            {
                resolved = (ModTier.Overhaul, "Marked as Overhaul.");
                confidence = 85;
            }
            else if (mod.ContainsWorldGenFiles || mod.ContainsPOIs || mod.ContainsBiomes || catText.Contains("poi") || catText.Contains("prefab") || catText.Contains("rwg") || catText.Contains("biome"))
            {
                resolved = (ModTier.WorldGen, "World generation files detected.");
                confidence = 90;
            }
            else if (mod.IsUI || category.Equals("XUI", StringComparison.OrdinalIgnoreCase) || catText.Contains("ui") || catText.Contains("hud"))
            {
                resolved = (ModTier.UI, "UI/XUI modification.");
                confidence = 85;
            }
            else if (mod.UsesXpath && (mod.Dependencies?.Any() == true))
            {
                resolved = (ModTier.Patch, "Uses XPaths + dependencies — treated as Patch.");
                confidence = 75;
            }
            else
            {
                resolved = (ModTier.Content, "Default content mod (heuristic classification).");
                confidence = 60;
            }

            mod.ResolvedTier = resolved.tier;
            mod.LoadReason = resolved.reason;
            mod.PlacementConfidence = Math.Max(0, Math.Min(confidence, 100));
            return resolved;
        }
    }
}
