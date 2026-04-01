namespace ModManager.Backend.Models
{
    public class ConflictInfo
    {
        public string ModA { get; set; } = string.Empty;
        public string ModB { get; set; } = string.Empty;
        public string Type { get; set; } = string.Empty;
        public string Severity { get; set; } = string.Empty;
    }
}
