using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Xml.Linq;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    public class ModScanner
    {
        public Task<IReadOnlyList<ModInfo>> ScanAsync(string modsRoot)
        {
            // IO-bound, but cheap enough; keep async-ready.
            return Task.Run<IReadOnlyList<ModInfo>>(() =>
            {
                var results = new List<ModInfo>();

                if (string.IsNullOrWhiteSpace(modsRoot))
                    return results;

                if (!Directory.Exists(modsRoot))
                    return results;

                try
                {
                    foreach (var dir in Directory.GetDirectories(modsRoot))
                    {
                        var folderName = Path.GetFileName(dir) ?? dir;
                        var found = "";
                        var hasDll = false;
                        var hasXml = false;
                        var usesXpath = false;
                        var xpathTargets = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                        var fileCount = 0;
                        string? modId = null;
                        string? modName = null;
                        List<string> dependencies = new List<string>();

                        // Structural hints for tier resolution.
                        var isCoreFramework = false;
                        var isOverhaul = false;
                        var isUi = false;
                        var containsWorldGenFiles = false;
                        var containsPois = false;
                        var containsBiomes = false;

                        try
                        {
                            found = Directory.GetFiles(dir, "ModInfo.xml", SearchOption.AllDirectories)
                                .FirstOrDefault() ?? "";
                        }
                        catch
                        {
                            found = "";
                        }

                        var has = !string.IsNullOrEmpty(found);

                        if (has)
                        {
                            try
                            {
                                var parsed = TryParseModInfo(found);
                                modId = parsed.Id;
                                modName = parsed.Name;
                                dependencies = parsed.Dependencies;
                            }
                            catch
                            {
                                // Parsing is best-effort; do not fail scan.
                                modId = null;
                                modName = null;
                                dependencies = new List<string>();
                            }
                        }

                        // Lightweight hints only; full collisions happen in conflict analysis.
                        try
                        {
                            // Shallow checks first.
                            hasDll = Directory.EnumerateFiles(dir, "*.dll", SearchOption.AllDirectories).Any();
                        }
                        catch { hasDll = false; }

                        // Count total files as a cheap proxy for "impact".
                        try
                        {
                            fileCount = Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories).Count();
                        }
                        catch
                        {
                            fileCount = 0;
                        }

                        // Cheap structural checks for known 7DTD folders/files.
                        try
                        {
                            // Common mod structure: <mod>/Config/*.xml and <mod>/Prefabs/*
                            var configDir = Path.Combine(dir, "Config");
                            var prefabsDir = Path.Combine(dir, "Prefabs");
                            var xuiDir = Path.Combine(dir, "XUi");

                            containsPois = Directory.Exists(prefabsDir);
                            isUi = Directory.Exists(xuiDir) || Directory.Exists(Path.Combine(dir, "XUI"));

                            if (Directory.Exists(configDir))
                            {
                                // File.Exists is case-insensitive on Windows.
                                containsWorldGenFiles = File.Exists(Path.Combine(configDir, "rwgmixer.xml"))
                                    || File.Exists(Path.Combine(configDir, "rwg.xml"))
                                    || File.Exists(Path.Combine(configDir, "worldgen.xml"));

                                containsBiomes = File.Exists(Path.Combine(configDir, "biomes.xml"))
                                    || File.Exists(Path.Combine(configDir, "biomes.xml".ToLowerInvariant()));
                            }
                        }
                        catch
                        {
                            // ignore
                        }

                        try
                        {
                            var xmlFiles = Directory.EnumerateFiles(dir, "*.xml", SearchOption.AllDirectories);
                            var xmlProcessed = 0;
                            foreach (var xf in xmlFiles)
                            {
                                xmlProcessed++;
                                if (xmlProcessed > 75)
                                    break;

                                hasXml = true;

                                // Structural inference from XML file names/paths.
                                try
                                {
                                    var xfName = Path.GetFileName(xf) ?? string.Empty;
                                    if (xfName.Equals("rwgmixer.xml", StringComparison.OrdinalIgnoreCase)
                                        || xfName.Equals("worldgen.xml", StringComparison.OrdinalIgnoreCase))
                                        containsWorldGenFiles = true;

                                    if (xfName.Equals("biomes.xml", StringComparison.OrdinalIgnoreCase))
                                        containsBiomes = true;

                                    if (xf.IndexOf("\\prefabs\\", StringComparison.OrdinalIgnoreCase) >= 0)
                                        containsPois = true;

                                    if (xf.IndexOf("\\xui\\", StringComparison.OrdinalIgnoreCase) >= 0
                                        || xf.IndexOf("\\xui", StringComparison.OrdinalIgnoreCase) >= 0)
                                        isUi = true;
                                }
                                catch { /* ignore */ }

                                // Read a small prefix for XPath usage signal.
                                try
                                {
                                    using var fs = File.OpenRead(xf);
                                    var buf = new byte[8192];
                                    var read = fs.Read(buf, 0, buf.Length);
                                    if (read > 0)
                                    {
                                        var s = System.Text.Encoding.UTF8.GetString(buf, 0, read);
                                        if (s.IndexOf("xpath", StringComparison.OrdinalIgnoreCase) >= 0)
                                            usesXpath = true;
                                    }
                                }
                                catch { /* ignore */ }

                                // Best-effort XPath target extraction.
                                // Only attempt if we already have some signal that the file uses xpath.
                                if (usesXpath)
                                {
                                    try
                                    {
                                        var fileInfo = new FileInfo(xf);
                                        // Avoid huge reads; 2MB is plenty for typical mod xml.
                                        var text = fileInfo.Length <= 2_000_000
                                            ? File.ReadAllText(xf)
                                            : string.Empty;

                                        if (!string.IsNullOrEmpty(text))
                                        {
                                            foreach (Match match in Regex.Matches(text, "xpath\\s*=\\s*\"([^\"]+)\"|xpath\\s*=\\s*'([^']+)'", RegexOptions.IgnoreCase))
                                            {
                                                var target = match.Groups[1].Success ? match.Groups[1].Value : match.Groups[2].Value;
                                                target = (target ?? string.Empty).Trim();
                                                if (target.Length > 0)
                                                    xpathTargets.Add(target);
                                            }
                                        }
                                    }
                                    catch { /* ignore */ }
                                }

                                // Do not break early: we want to collect XPathTargets across files.
                            }
                        }
                        catch { hasXml = false; usesXpath = false; }

                        // Name-based hints (fallback if categories aren't computed yet).
                        var nameText = ((modName ?? folderName) + " " + folderName).ToLowerInvariant();
                        if (folderName.StartsWith("0-", StringComparison.OrdinalIgnoreCase)
                            || nameText.Contains("core")
                            || nameText.Contains("framework")
                            || nameText.Contains("api"))
                            isCoreFramework = true;

                        if (nameText.Contains("overhaul") || nameText.Contains("total conversion"))
                            isOverhaul = true;

                        if (nameText.Contains("ui") || nameText.Contains("hud") || nameText.Contains("xui"))
                            isUi = true;

                        results.Add(new ModInfo
                        {
                            Id = (modId ?? string.Empty).Trim(),
                            Name = !string.IsNullOrWhiteSpace(modName) ? modName!.Trim() : folderName,
                            FolderName = folderName,
                            ModRootPath = Path.GetFullPath(dir),
                            Enabled = true,
                            Category = "",
                            Dependencies = dependencies ?? new List<string>(),
                            XPathTargets = xpathTargets.ToList(),
                            IsCoreFramework = isCoreFramework,
                            IsOverhaul = isOverhaul,
                            IsUI = isUi,
                            ContainsWorldGenFiles = containsWorldGenFiles,
                            ContainsPOIs = containsPois,
                            ContainsBiomes = containsBiomes,
                            LoadReason = string.Empty,
                            LoadOrder = 0,
                            HasModInfo = has,
                            ModInfoPath = has ? Path.GetFullPath(found) : string.Empty,
                            Status = has ? "OK" : "Missing ModInfo.xml",
                            HasDll = hasDll,
                            HasXml = hasXml,
                            UsesXpath = usesXpath,
                            LoadImpactScore = fileCount switch
                            {
                                < 10 => 10,
                                < 50 => 30,
                                < 150 => 60,
                                < 300 => 80,
                                _ => 100
                            },
                        });
                    }
                }
                catch
                {
                    // Swallow: caller decides how to report.
                }

                // Finalize identity fields.
                foreach (var mod in results)
                {
                    if (string.IsNullOrWhiteSpace(mod.Id))
                        mod.Id = mod.FolderName;
                }

                return results
                    .OrderBy(m => m.FolderName, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            });
        }

        private static (string? Id, string? Name, List<string> Dependencies) TryParseModInfo(string modInfoPath)
        {
            // 7DTD ModInfo.xml variants exist; keep this resilient and best-effort.
            // We intentionally avoid throwing for unknown shapes.
            var deps = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            XDocument doc;
            using (var fs = File.OpenRead(modInfoPath))
            {
                doc = XDocument.Load(fs, LoadOptions.None);
            }

            var root = doc.Root;
            if (root == null)
                return (null, null, new List<string>());

            string? ReadFirstDescendantValue(params string[] localNames)
            {
                foreach (var ln in localNames)
                {
                    var el = root.Descendants().FirstOrDefault(e => string.Equals(e.Name.LocalName, ln, StringComparison.OrdinalIgnoreCase));
                    var val = el?.Value;
                    if (!string.IsNullOrWhiteSpace(val))
                        return val.Trim();
                }
                return null;
            }

            var id = ReadFirstDescendantValue("Id", "ModId", "ModID", "UniqueId", "UniqueID");
            var name = ReadFirstDescendantValue("Name", "ModName", "Title");

            // Dependency extraction: look for common patterns and attribute names.
            static string? GetAttr(XElement el, params string[] names)
            {
                foreach (var n in names)
                {
                    var a = el.Attributes().FirstOrDefault(x => string.Equals(x.Name.LocalName, n, StringComparison.OrdinalIgnoreCase));
                    if (a != null && !string.IsNullOrWhiteSpace(a.Value))
                        return a.Value.Trim();
                }
                return null;
            }

            bool IsContainerName(string ln)
                => ln.Equals("Dependencies", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("ModDependencies", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("Requires", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("RequiredMods", StringComparison.OrdinalIgnoreCase);

            bool IsDependencyElementName(string ln)
                => ln.Equals("Dependency", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("DependsOn", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("ModDependency", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("RequiredMod", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("Require", StringComparison.OrdinalIgnoreCase)
                || ln.Equals("Requires", StringComparison.OrdinalIgnoreCase);

            foreach (var container in root.Descendants().Where(e => IsContainerName(e.Name.LocalName)))
            {
                foreach (var el in container.Descendants())
                {
                    var ln = el.Name.LocalName;
                    if (!IsDependencyElementName(ln) && !ln.Equals("Mod", StringComparison.OrdinalIgnoreCase))
                        continue;

                    var dep = GetAttr(el, "Id", "ModId", "modId", "Name", "name") ?? (string.IsNullOrWhiteSpace(el.Value) ? null : el.Value.Trim());
                    if (!string.IsNullOrWhiteSpace(dep))
                        deps.Add(dep);
                }
            }

            // Fallback: any explicit <Dependency ...> anywhere.
            foreach (var el in root.Descendants().Where(e => IsDependencyElementName(e.Name.LocalName)))
            {
                var dep = GetAttr(el, "Id", "ModId", "modId", "Name", "name") ?? (string.IsNullOrWhiteSpace(el.Value) ? null : el.Value.Trim());
                if (!string.IsNullOrWhiteSpace(dep))
                    deps.Add(dep);
            }

            return (
                string.IsNullOrWhiteSpace(id) ? null : id,
                string.IsNullOrWhiteSpace(name) ? null : name,
                deps.Where(d => !string.IsNullOrWhiteSpace(d)).OrderBy(d => d, StringComparer.OrdinalIgnoreCase).ToList()
            );
        }
    }
}
