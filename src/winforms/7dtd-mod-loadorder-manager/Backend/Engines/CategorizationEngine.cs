using System;
using System.Collections.Generic;
using System.Linq;
using ModManager.Backend.Models;

namespace ModManager.Backend.Engines
{
    public sealed class CategorizationEngine
    {
        public IReadOnlyList<string> Categorize(ModInfo mod)
        {
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            var text = (mod.Name + " " + mod.FolderName + " " + mod.Status).Trim();
            if (string.IsNullOrWhiteSpace(text))
                return Array.Empty<string>();

            AddByKeywords(results, text);

            // Normalize to contract names.
            return results.Select(CategoryNames.Normalize)
                .Where(n => !string.IsNullOrWhiteSpace(n))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static void AddByKeywords(HashSet<string> results, string text)
        {
            var t = text.ToLowerInvariant();

            // Basic heuristic mapping. This is intentionally conservative.
            if (ContainsAny(t, "ui", "hud", "interface", "menu")) results.Add("UI");
            if (ContainsAny(t, "weapon", "gun", "rifle", "pistol")) results.Add("Weapons");
            if (ContainsAny(t, "zombie", "creature", "animal")) results.Add("Zombies/Creatures");
            if (ContainsAny(t, "quest", "trader")) results.Add("Quests");
            if (ContainsAny(t, "poi", "prefab")) results.Add("Prefabs/POIs");
            if (ContainsAny(t, "performance", "fps", "optimiz")) results.Add("Performance");
            if (ContainsAny(t, "craft", "recipe")) results.Add("Crafting");
            if (ContainsAny(t, "gameplay", "balance", "difficulty")) results.Add("Gameplay");
            if (ContainsAny(t, "loot", "item")) results.Add("Items_Loot");
            if (ContainsAny(t, "overhaul", "total conversion")) results.Add("Overhauls");
            if (ContainsAny(t, "xml", "xpath")) results.Add("XML Edits");
            if (ContainsAny(t, "library", "dependency", "dll")) results.Add("Libraries/Dependencies");
            if (ContainsAny(t, "visual", "audio", "sound", "music", "texture")) results.Add("Visual/Audio");
        }

        private static bool ContainsAny(string haystack, params string[] needles)
        {
            foreach (var n in needles)
            {
                if (haystack.Contains(n))
                    return true;
            }
            return false;
        }
    }
}
