using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace ModManager.Backend.Models
{
    public sealed class BackendState
    {
        public List<ModInfo> Mods { get; set; } = new List<ModInfo>();
        public List<CategorySummary> Categories { get; set; } = new List<CategorySummary>();
        public Totals Totals { get; set; } = new Totals();
        public BackendError? Error { get; set; }

        public static BackendState Empty(string? message = null)
        {
            return new BackendState
            {
                Mods = new List<ModInfo>(),
                Categories = CategorySummary.EmptyAllCategories(),
                Totals = new Totals(),
                Error = string.IsNullOrWhiteSpace(message) ? null : new BackendError { Message = message }
            };
        }
    }

    public sealed class Totals
    {
        public int Mods { get; set; }
        public int Enabled { get; set; }
        public int Disabled { get; set; }
        public int Conflicts { get; set; }

        // Internal counter (required by backend responsibilities), but excluded from strict JSON contract.
        [JsonIgnore]
        public int RedundantMods { get; set; }
    }

    public sealed class BackendError
    {
        public string Message { get; set; } = string.Empty;
        public string Code { get; set; } = string.Empty;
        public string? Details { get; set; }
    }
}
