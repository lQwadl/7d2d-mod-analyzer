using System;
using System.Collections.Generic;
using ModManager.Backend.Models;

namespace ModManager.Backend.Ports
{
    // Output + input port for the WinForms host.
    // Backend never touches UI controls; UI implements this interface.
    public interface IUiPort
    {
        string ModsPath { get; }

        void InvokeOnUi(Action action);

        void SetMods(IReadOnlyList<ModInfo> mods);

        void ShowInfo(string title, string message);
        void ShowWarning(string title, string message);
        void ShowError(string title, string message);
    }
}
