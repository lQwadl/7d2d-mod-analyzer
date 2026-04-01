using System;
using ModManager.Backend.Ports;

namespace ModManagerPrototype
{
    internal static class Form1BackendHost
    {
        public static void Wire(Form1 form)
        {
            if (form == null)
                throw new ArgumentNullException(nameof(form));

            // UI -> Backend
            form.UIEventHandler = new BackendUiEventHandler();

            // Backend -> UI (authoritative snapshots)
            PortHandlers.Initialize(new Form1UiPort(form));
            PortHandlers.OnPortEmitted += form.HandleUIEvent;

            form.FormClosed += (_, __) =>
            {
                PortHandlers.OnPortEmitted -= form.HandleUIEvent;
            };
        }

        private sealed class BackendUiEventHandler : IUIEventHandler
        {
            public void HandleUIEvent(PortData eventData)
            {
                _ = UIEventDispatcher.DispatchAsync(eventData);
            }
        }

        private sealed class Form1UiPort : IUiPort
        {
            private readonly Form1 _form;

            public Form1UiPort(Form1 form)
            {
                _form = form;
            }

            public string ModsPath => _form?.GetModsPath() ?? string.Empty;

            public void InvokeOnUi(Action action)
            {
                if (action == null)
                    return;

                if (_form == null || _form.IsDisposed)
                    return;

                if (_form.InvokeRequired)
                    _form.BeginInvoke(action);
                else
                    action();
            }

            public void SetMods(System.Collections.Generic.IReadOnlyList<ModManager.Backend.Models.ModInfo> mods)
            {
                // Intentionally no-op.
                // Form1 renders via BackendSnapshot emitted on PortHandlers.OnPortEmitted.
            }

            public void ShowInfo(string title, string message)
                => InvokeOnUi(() => System.Windows.Forms.MessageBox.Show(_form, message, title, System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Information));

            public void ShowWarning(string title, string message)
                => InvokeOnUi(() => System.Windows.Forms.MessageBox.Show(_form, message, title, System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Warning));

            public void ShowError(string title, string message)
                => InvokeOnUi(() => System.Windows.Forms.MessageBox.Show(_form, message, title, System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Error));
        }
    }
}
