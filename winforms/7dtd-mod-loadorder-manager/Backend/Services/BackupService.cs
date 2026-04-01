using System.Threading.Tasks;

namespace ModManager.Backend.Services
{
    public class BackupService
    {
        public Task BackupModsAsync() => Task.CompletedTask;
        public Task RestoreBackupAsync() => Task.CompletedTask;
    }
}
