using System;
using System.Collections.Generic;
using System.Linq;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    public sealed class BackendStateBuilder
    {
        private readonly CategorizationEngine _categorizer;

        public BackendStateBuilder(CategorizationEngine categorizer)
        {
            _categorizer = categorizer;
        }

        public BackendState Build(IReadOnlyList<ModInfo> mods, IReadOnlyList<ModConflictSummary> conflicts)
        {
            mods ??= Array.Empty<ModInfo>();
            conflicts ??= Array.Empty<ModConflictSummary>();

            var redundantNames = new HashSet<string>(
                mods.Where(m => !string.IsNullOrWhiteSpace(m.Name))
                    .GroupBy(m => m.Name.Trim(), StringComparer.OrdinalIgnoreCase)
                    .Where(g => g.Count() > 1)
                    .Select(g => g.Key),
                StringComparer.OrdinalIgnoreCase);

            // Apply categories per mod (multi-category supported).
            foreach (var mod in mods)
            {
                mod.Categories = _categorizer.Categorize(mod).ToList();
                mod.Category = mod.Categories.FirstOrDefault() ?? string.Empty;
            }

            var totals = new Totals
            {
                Mods = mods.Count,
                Enabled = mods.Count(m => m.Enabled),
                Disabled = mods.Count(m => !m.Enabled),
                Conflicts = conflicts.Sum(c => c.ConflictCount),
                RedundantMods = mods.GroupBy(m => (m.Name ?? string.Empty).Trim(), StringComparer.OrdinalIgnoreCase)
                    .Count(g => g.Key.Length > 0 && g.Count() > 1)
            };

            // Category summaries. Must include empty categories when no mods exist.
            var categories = CategorySummary.EmptyAllCategories();
            var categoryIndex = categories.ToDictionary(c => c.Name, StringComparer.OrdinalIgnoreCase);

            foreach (var mod in mods)
            {
                foreach (var cat in mod.Categories)
                {
                    var normalized = CategoryNames.Normalize(cat);
                    if (string.IsNullOrWhiteSpace(normalized))
                        continue;

                    if (!categoryIndex.TryGetValue(normalized, out var summary))
                        continue;

                    summary.ModCount += 1;

                    var modConflict = conflicts.FirstOrDefault(c => c.Matches(mod));
                    var conflictCount = modConflict?.ConflictCount ?? 0;
                    summary.ConflictCount += conflictCount;

                    // Severity keys must be: Critical, High, Low, Redundant, Disabled, OK.
                    // Count each mod exactly once into the distribution.
                    if (!mod.Enabled)
                    {
                        summary.SeverityDistribution.Disabled += 1;
                        continue;
                    }

                    var isRedundant = !string.IsNullOrWhiteSpace(mod.Name) && redundantNames.Contains(mod.Name.Trim());
                    if (isRedundant)
                    {
                        summary.SeverityDistribution.Redundant += 1;
                        continue;
                    }

                    if (conflictCount <= 0)
                    {
                        summary.SeverityDistribution.OK += 1;
                        continue;
                    }

                    // Map internal severity to the required output buckets.
                    var severity = modConflict?.MaxSeverity ?? Severity.Low;
                    if (severity == Severity.Critical)
                        summary.SeverityDistribution.Critical += 1;
                    else if (severity == Severity.High)
                        summary.SeverityDistribution.High += 1;
                    else
                        summary.SeverityDistribution.Low += 1;
                }
            }

            foreach (var summary in categories)
            {
                if (summary.ModCount <= 0)
                {
                    summary.Percentage = 0.0;
                    continue;
                }

                // riskPercent = (conflictedMods / totalModsInCategory) * 100
                var conflictedMods = summary.SeverityDistribution.Critical
                    + summary.SeverityDistribution.High
                    + summary.SeverityDistribution.Low
                    + summary.SeverityDistribution.Redundant;

                summary.Percentage = (double)conflictedMods / summary.ModCount * 100.0;
            }

            return new BackendState
            {
                Mods = mods.ToList(),
                Categories = categories,
                Totals = totals,
                Error = null
            };
        }
    }

    public sealed class ModConflictSummary
    {
        public string ModName { get; set; } = string.Empty;
        public string FolderName { get; set; } = string.Empty;
        public int ConflictCount { get; set; }
        public Severity MaxSeverity { get; set; } = Severity.Low;

        public bool Matches(ModInfo mod)
        {
            if (!string.IsNullOrWhiteSpace(ModName) && string.Equals(ModName, mod.Name, StringComparison.OrdinalIgnoreCase))
                return true;
            if (!string.IsNullOrWhiteSpace(FolderName) && string.Equals(FolderName, mod.FolderName, StringComparison.OrdinalIgnoreCase))
                return true;
            return false;
        }
    }
}
