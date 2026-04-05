using System.Threading.Tasks;

namespace ModManager.Backend.Services
{
    public class ProfileService
    {
        public Task CreateProfileAsync() => Task.CompletedTask;
        public Task DeleteProfileAsync() => Task.CompletedTask;
        public Task SwitchProfileAsync(string profileName) => Task.CompletedTask;
    }
}
