using System;

namespace SevenDays.ModManager
{
    // Simple model representing a scanned mod folder
    public class ModInfoResult
    {
        public int LoadOrder { get; set; }
        public string FolderName { get; set; }
        public bool HasModInfo { get; set; }
        public string ModInfoPath { get; set; }
        public string Status { get; set; }

        public ModInfoResult()
        {
            LoadOrder = 0;
            FolderName = string.Empty;
            HasModInfo = false;
            ModInfoPath = string.Empty;
            Status = "Unknown";
        }
    }
}
