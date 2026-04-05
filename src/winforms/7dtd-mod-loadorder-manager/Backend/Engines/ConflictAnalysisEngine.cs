using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    /// <summary>
    /// Backend-owned conflict detection + severity calculation.
    /// No UI assumptions; returns structured summaries usable for state building.
    /// </summary>
    public sealed class ConflictAnalysisEngine
    {
        public Task<IReadOnlyList<ModConflictSummary>> AnalyzeAsync(string modsRoot, IReadOnlyList<ModInfo> mods, bool deepFileCollisionScan)
        {
            return Task.Run<IReadOnlyList<ModConflictSummary>>(() =>
            {
                mods ??= Array.Empty<ModInfo>();

                var summaries = mods.Select(m => new ModConflictSummary
                {
                    ModName = m.Name,
                    FolderName = m.FolderName,
                    ConflictCount = 0,
                    MaxSeverity = Severity.Low
                }).ToList();

                var byFolder = summaries.ToDictionary(s => s.FolderName ?? string.Empty, StringComparer.OrdinalIgnoreCase);

                // 1) Duplicate mod identifiers (name duplicates) => Medium.
                foreach (var group in mods
                    .Where(m => !string.IsNullOrWhiteSpace(m.Name))
                    .GroupBy(m => m.Name.Trim(), StringComparer.OrdinalIgnoreCase)
                    .Where(g => g.Count() > 1))
                {
                    foreach (var mod in group)
                        Bump(byFolder, mod.FolderName, 1, Severity.Medium);
                }

                // 2) DLL conflicts: same DLL filename appears in multiple mods => High.
                var dllOwners = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                foreach (var mod in mods)
                {
                    if (string.IsNullOrWhiteSpace(mod.ModRootPath) || !Directory.Exists(mod.ModRootPath))
                        continue;

                    IEnumerable<string> dlls;
                    try { dlls = Directory.EnumerateFiles(mod.ModRootPath, "*.dll", SearchOption.AllDirectories); }
                    catch { continue; }

                    foreach (var dll in dlls)
                    {
                        var dllName = Path.GetFileName(dll) ?? dll;
                        if (dllOwners.TryGetValue(dllName, out var existingOwnerFolder))
                        {
                            Bump(byFolder, existingOwnerFolder, 1, Severity.High);
                            Bump(byFolder, mod.FolderName, 1, Severity.High);
                        }
                        else
                        {
                            dllOwners[dllName] = mod.FolderName;
                        }
                    }
                }

                // 3) XPath clashes: if multiple mods use xpath, treat as Medium risk for those mods.
                var xpathMods = mods.Where(m => m.UsesXpath).ToList();
                if (xpathMods.Count > 1)
                {
                    foreach (var mod in xpathMods)
                        Bump(byFolder, mod.FolderName, 1, Severity.Medium);
                }

                // 4) Load order violations: duplicate load order values among enabled mods => Medium.
                foreach (var group in mods.Where(m => m.Enabled).GroupBy(m => m.LoadOrder).Where(g => g.Key > 0 && g.Count() > 1))
                {
                    foreach (var mod in group)
                        Bump(byFolder, mod.FolderName, 1, Severity.Medium);
                }

                // 5) File overwrite collisions (deep scan): same relative path in multiple mods.
                if (deepFileCollisionScan && !string.IsNullOrWhiteSpace(modsRoot) && Directory.Exists(modsRoot))
                {
                    var seen = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                    foreach (var mod in mods)
                    {
                        if (string.IsNullOrWhiteSpace(mod.ModRootPath) || !Directory.Exists(mod.ModRootPath))
                            continue;

                        IEnumerable<string> files;
                        try { files = Directory.EnumerateFiles(mod.ModRootPath, "*", SearchOption.AllDirectories); }
                        catch { continue; }

                        foreach (var file in files)
                        {
                            var rel = SafeRelative(mod.ModRootPath, file);
                            if (string.IsNullOrWhiteSpace(rel))
                                continue;

                            // Ignore ModInfo.xml collisions (common name but per-folder).
                            if (string.Equals(Path.GetFileName(rel), "ModInfo.xml", StringComparison.OrdinalIgnoreCase))
                                continue;

                            if (seen.TryGetValue(rel, out var ownerFolder))
                            {
                                var ext = Path.GetExtension(rel);
                                var sev = string.Equals(ext, ".dll", StringComparison.OrdinalIgnoreCase)
                                    ? Severity.Critical
                                    : Severity.High;

                                Bump(byFolder, ownerFolder, 1, sev);
                                Bump(byFolder, mod.FolderName, 1, sev);
                            }
                            else
                            {
                                seen[rel] = mod.FolderName;
                            }
                        }
                    }
                }

                return summaries
                    .OrderByDescending(s => s.MaxSeverity)
                    .ThenByDescending(s => s.ConflictCount)
                    .ThenBy(s => s.FolderName, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            });
        }

        private static void Bump(Dictionary<string, ModConflictSummary> byFolder, string? folderName, int count, Severity severity)
        {
            folderName ??= string.Empty;
            if (!byFolder.TryGetValue(folderName, out var s))
                return;

            s.ConflictCount += count;
            if (severity > s.MaxSeverity)
                s.MaxSeverity = severity;
        }

        private static string SafeRelative(string root, string path)
        {
            try
            {
                var r = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                var p = Path.GetFullPath(path);
                if (!p.StartsWith(r, StringComparison.OrdinalIgnoreCase))
                    return string.Empty;
                var rel = p.Substring(r.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                return rel.Replace(Path.DirectorySeparatorChar, '/').Replace(Path.AltDirectorySeparatorChar, '/');
            }
            catch
            {
                return string.Empty;
            }
        }
    }
}
