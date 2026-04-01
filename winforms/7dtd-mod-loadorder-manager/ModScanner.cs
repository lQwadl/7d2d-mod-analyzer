using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace SevenDays.ModManager
{
    public class ModScanner
    {
        // Scan first-level subdirectories under modsRoot and look for ModInfo.xml
        public List<ModInfoResult> Scan(string modsRoot)
        {
            var results = new List<ModInfoResult>();

            if (string.IsNullOrWhiteSpace(modsRoot)) return results;
            if (!Directory.Exists(modsRoot)) return results;

            try
            {
                var subdirs = Directory.GetDirectories(modsRoot);
                foreach (var d in subdirs)
                {
                    var res = new ModInfoResult();
                    res.FolderName = Path.GetFileName(d) ?? d;
                    res.LoadOrder = 0;

                    try
                    {
                        var found = Directory.GetFiles(d, "ModInfo.xml", SearchOption.AllDirectories).FirstOrDefault();
                        if (!string.IsNullOrEmpty(found))
                        {
                            res.HasModInfo = true;
                            res.ModInfoPath = Path.GetFullPath(found);
                            res.Status = "OK";
                        }
                        else
                        {
                            res.HasModInfo = false;
                            res.ModInfoPath = string.Empty;
                            res.Status = "Missing ModInfo.xml";
                        }
                    }
                    catch
                    {
                        res.HasModInfo = false;
                        res.ModInfoPath = string.Empty;
                        res.Status = "Error scanning folder";
                    }

                    results.Add(res);
                }
            }
            catch
            {
                // swallow and return what we have; UI will show errors
            }

            // Sort alphabetically by folder name
            results = results.OrderBy(r => r.FolderName, StringComparer.OrdinalIgnoreCase).ToList();
            return results;
        }
    }
}
