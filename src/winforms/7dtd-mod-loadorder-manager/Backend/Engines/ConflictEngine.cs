using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    public class ConflictEngine
    {
        private readonly ConflictAnalysisEngine _analyzer = new ConflictAnalysisEngine();

        // Back-compat: original stub signature.
        public Task ScanConflictsAsync() => Task.CompletedTask;

        public Task<IReadOnlyList<ModConflictSummary>> AnalyzeAsync(string modsRoot, IReadOnlyList<ModInfo> mods, bool deepFileCollisionScan)
        {
            mods ??= Array.Empty<ModInfo>();
            return _analyzer.AnalyzeAsync(modsRoot, mods, deepFileCollisionScan);
        }
    }
}
