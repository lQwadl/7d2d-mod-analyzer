using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace ModManager.Backend.Models
{
    public sealed class CategorySummary
    {
        public string Name { get; set; } = string.Empty;
        public int ModCount { get; set; }
        public int ConflictCount { get; set; }
        public SeverityDistribution SeverityDistribution { get; set; } = new SeverityDistribution();
        public double Percentage { get; set; }

        public static List<CategorySummary> EmptyAllCategories()
        {
            var list = new List<CategorySummary>();
            foreach (var name in CategoryNames.All)
            {
                list.Add(new CategorySummary
                {
                    Name = name,
                    ModCount = 0,
                    ConflictCount = 0,
                    SeverityDistribution = new SeverityDistribution(),
                    Percentage = 0.0
                });
            }
            return list;
        }
    }

    public static class CategoryNames
    {
        public static readonly string[] All = new[]
        {
            "Crafting",
            "Gameplay",
            "Items_Loot",
            "Libraries/Dependencies",
            "Overhauls",
            "Performance",
            "Prefabs/POIs",
            "Quests",
            "UI",
            "Visual/Audio",
            "Weapons",
            "XML Edits",
            "Zombies/Creatures"
        };

        public static string Normalize(string name)
        {
            if (string.IsNullOrWhiteSpace(name))
                return string.Empty;

            foreach (var n in All)
            {
                if (string.Equals(n, name.Trim(), StringComparison.OrdinalIgnoreCase))
                    return n;
            }

            return name.Trim();
        }
    }

    public sealed class SeverityDistribution
    {
        [JsonPropertyName("Critical")]
        public int Critical { get; set; }

        [JsonPropertyName("High")]
        public int High { get; set; }

        [JsonPropertyName("Low")]
        public int Low { get; set; }

        [JsonPropertyName("Redundant")]
        public int Redundant { get; set; }

        [JsonPropertyName("Disabled")]
        public int Disabled { get; set; }

        [JsonPropertyName("OK")]
        public int OK { get; set; }
    }

    public enum Severity
    {
        Low = 0,
        Medium = 1,
        High = 2,
        Critical = 3
    }
}
