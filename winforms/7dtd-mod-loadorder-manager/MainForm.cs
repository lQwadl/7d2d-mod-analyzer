using System;
using System.ComponentModel;
using System.Linq;
using System.Windows.Forms;

using ModManager.Backend.Models;
using ModManager.Backend.Ports;
using ModManagerPrototype;

namespace SevenDays.ModManager
{
    public class MainForm : Form
    {
        private TextBox txtModsPath = null!;
        private Button btnBrowse = null!;
        private Button btnScan = null!;
        private Button btnGenerate = null!;
        private Button btnExport = null!;
        private Button btnExportVortex = null!;
        private Button btnDiagnostics = null!;
        private DataGridView dgvMods = null!;
        private Label lblModsPath = null!;

        private readonly BindingList<ModInfo> _mods = new BindingList<ModInfo>();

        private BackendSnapshot? _lastSnapshot;

        public MainForm()
        {
            InitializeComponent();

            // Connect UI to backend via ports/handlers.
            PortHandlers.Initialize(new WinFormsUiPort(this));

            // Backend emits direct object-graph snapshots; UI can render immediately without parsing.
            PortHandlers.OnPortEmitted += OnBackendPortEmitted;
        }

        private void OnBackendPortEmitted(PortData e)
        {
            if (e is null)
                return;

            if (e.Port != PortContract.PortIds.GetBackendSnapshot)
                return;

            if (e.Data is BackendSnapshot snapshot)
            {
                _lastSnapshot = snapshot;

                // Current UI only binds mods grid; keep UI logic minimal.
                _mods.Clear();
                if (snapshot.Mods != null)
                {
                    foreach (var m in snapshot.Mods)
                        _mods.Add(m);
                }
            }
        }

        private void InitializeComponent()
        {
            this.Text = "7DTD Mod Load Order Manager";
            this.Width = 900;
            this.Height = 600;
            this.StartPosition = FormStartPosition.CenterScreen;

            lblModsPath = new Label() { Left = 10, Top = 14, Text = "Mods Path:", AutoSize = true };
            this.Controls.Add(lblModsPath);

            txtModsPath = new TextBox() { Left = 90, Top = 10, Width = 600 };
            txtModsPath.Text = @"C:\Program Files (x86)\Steam\steamapps\common\7 Days To Die\Mods";
            this.Controls.Add(txtModsPath);

            btnBrowse = new Button() { Left = 700, Top = 8, Width = 80, Text = "Browse" };
            btnBrowse.Click += Port_BrowseModsPathClicked;
            this.Controls.Add(btnBrowse);

            btnScan = new Button() { Left = 10, Top = 44, Width = 120, Text = "Scan Mods" };
            btnScan.Click += Port_ScanModsClicked;
            this.Controls.Add(btnScan);

            btnGenerate = new Button() { Left = 140, Top = 44, Width = 140, Text = "Generate Load Order" };
            btnGenerate.Click += Port_GenerateLoadOrderClicked;
            this.Controls.Add(btnGenerate);

            btnExport = new Button() { Left = 290, Top = 44, Width = 120, Text = "Export JSON" };
            btnExport.Click += Port_ExportJsonClicked;
            this.Controls.Add(btnExport);

            btnExportVortex = new Button() { Left = 420, Top = 44, Width = 120, Text = "Export Vortex" };
            btnExportVortex.Click += Port_ExportVortexClicked;
            this.Controls.Add(btnExportVortex);

            btnDiagnostics = new Button() { Left = 550, Top = 44, Width = 120, Text = "Diagnostics" };
            btnDiagnostics.Click += BtnDiagnostics_Click;
            this.Controls.Add(btnDiagnostics);

            dgvMods = new DataGridView()
            {
                Left = 10,
                Top = 80,
                Width = 860,
                Height = 460,
                AutoGenerateColumns = false,
                AllowUserToAddRows = false,
                ReadOnly = false
            };

            dgvMods.ShowCellToolTips = true;
            dgvMods.CellToolTipTextNeeded += DgvMods_CellToolTipTextNeeded;
            dgvMods.CellFormatting += DgvMods_CellFormatting;
            dgvMods.RowPrePaint += DgvMods_RowPrePaint;

            // Columns: LoadOrder, Tier, Confidence, Conflict, XPathOverlap, Impact, MissingDeps, FolderName, HasModInfo, ModInfoPath, Status
            var colLoad = new DataGridViewTextBoxColumn() { HeaderText = "LoadOrder", DataPropertyName = "LoadOrder", Width = 80 };
            var colTier = new DataGridViewTextBoxColumn() { HeaderText = "Tier", DataPropertyName = nameof(ModInfo.ResolvedTier), Width = 80, ReadOnly = true };
            var colConfidence = new DataGridViewTextBoxColumn()
            {
                HeaderText = "Confidence",
                DataPropertyName = nameof(ModInfo.PlacementConfidence),
                Width = 90,
                ReadOnly = true,
                DefaultCellStyle = { Format = "0'%'" }
            };

            var colUiOverride = new DataGridViewCheckBoxColumn()
            {
                Name = "IsUiOverride",
                HeaderText = "UI Override?",
                DataPropertyName = nameof(ModInfo.IsUiOverride),
                Width = 90,
                ReadOnly = true
            };

            var colUiOverrideRank = new DataGridViewTextBoxColumn()
            {
                Name = "UiOverrideRank",
                HeaderText = "UI Override Rank",
                DataPropertyName = nameof(ModInfo.UiOverrideRank),
                Width = 110,
                ReadOnly = true
            };

            var colConflict = new DataGridViewCheckBoxColumn()
            {
                Name = "Conflict",
                HeaderText = "Conflict",
                DataPropertyName = nameof(ModInfo.HasConflict),
                Width = 70,
                ReadOnly = true
            };

            var colOverlap = new DataGridViewTextBoxColumn()
            {
                Name = "XPathOverlap",
                HeaderText = "XPath Overlap",
                DataPropertyName = nameof(ModInfo.XPathOverlapCount),
                Width = 95,
                ReadOnly = true
            };

            var colImpact = new DataGridViewTextBoxColumn()
            {
                Name = "Impact",
                HeaderText = "Impact",
                DataPropertyName = nameof(ModInfo.LoadImpactScore),
                Width = 70,
                ReadOnly = true,
                DefaultCellStyle = { Format = "0'%'" }
            };

            var colMissing = new DataGridViewTextBoxColumn()
            {
                Name = "MissingDeps",
                HeaderText = "Missing Deps",
                Width = 180,
                ReadOnly = true
            };

            var colFolder = new DataGridViewTextBoxColumn() { HeaderText = "FolderName", DataPropertyName = "FolderName", Width = 200, ReadOnly = true };
            var colHas = new DataGridViewCheckBoxColumn() { HeaderText = "HasModInfo", DataPropertyName = "HasModInfo", Width = 80 };
            var colPath = new DataGridViewTextBoxColumn() { HeaderText = "ModInfoPath", DataPropertyName = "ModInfoPath", Width = 360, ReadOnly = true };
            var colStatus = new DataGridViewTextBoxColumn() { HeaderText = "Status", DataPropertyName = "Status", Width = 120, ReadOnly = true };

            dgvMods.Columns.AddRange(new DataGridViewColumn[] { colLoad, colTier, colConfidence, colUiOverride, colUiOverrideRank, colConflict, colOverlap, colImpact, colMissing, colFolder, colHas, colPath, colStatus });
            dgvMods.DataSource = _mods;
            this.Controls.Add(dgvMods);
        }

        private void DgvMods_RowPrePaint(object? sender, DataGridViewRowPrePaintEventArgs e)
        {
            if (e.RowIndex < 0)
                return;

            if (dgvMods.Rows[e.RowIndex].DataBoundItem is not ModInfo mod)
                return;

            var row = dgvMods.Rows[e.RowIndex];

            // Reset
            row.DefaultCellStyle.BackColor = dgvMods.DefaultCellStyle.BackColor;
            row.DefaultCellStyle.Font = dgvMods.Font;

            if (mod.HasConflict)
                row.DefaultCellStyle.BackColor = Color.MistyRose;
            else if (mod.MissingDependencies != null && mod.MissingDependencies.Any())
                row.DefaultCellStyle.BackColor = Color.LightYellow;

            if (mod.IsUiOverride)
            {
                row.DefaultCellStyle.Font = new Font(dgvMods.Font, FontStyle.Bold);
                if (!mod.HasConflict && (mod.MissingDependencies == null || !mod.MissingDependencies.Any()))
                    row.DefaultCellStyle.BackColor = Color.LightGoldenrodYellow;
            }
        }

        private void DgvMods_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
        {
            if (e.RowIndex < 0)
                return;

            if (dgvMods.Columns[e.ColumnIndex].Name != "MissingDeps")
                return;

            if (dgvMods.Rows[e.RowIndex].DataBoundItem is not ModInfo mod)
                return;

            e.Value = (mod.MissingDependencies != null && mod.MissingDependencies.Any())
                ? string.Join(", ", mod.MissingDependencies)
                : string.Empty;
            e.FormattingApplied = true;
        }

        private void BtnDiagnostics_Click(object? sender, EventArgs e)
        {
            if (dgvMods.CurrentRow?.DataBoundItem is not ModInfo mod)
            {
                MessageBox.Show("Select a mod row first.", "Diagnostics", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            var title = string.IsNullOrWhiteSpace(mod.Name) ? (mod.FolderName ?? "Mod") : mod.Name;
            var message =
                $"Tier: {mod.ResolvedTier}\r\n" +
                $"Confidence: {mod.PlacementConfidence}%\r\n" +
                $"\r\nReason:\r\n{mod.LoadReason}";

            MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void DgvMods_CellToolTipTextNeeded(object? sender, DataGridViewCellToolTipTextNeededEventArgs e)
        {
            if (e.RowIndex < 0)
                return;

            if (dgvMods.Rows[e.RowIndex].DataBoundItem is ModInfo mod)
                e.ToolTipText = mod.LoadReason ?? string.Empty;
        }

        private void Port_BrowseModsPathClicked(object? sender, EventArgs e)
        {
            using var dlg = new FolderBrowserDialog();
            dlg.Description = "Select Mods folder";
            dlg.SelectedPath = txtModsPath.Text;
            if (dlg.ShowDialog() == DialogResult.OK)
            {
                txtModsPath.Text = dlg.SelectedPath;
            }
        }

        private async void Port_ScanModsClicked(object? sender, EventArgs e)
        {
            await PortHandlers.HandleScanModsAsync();
        }

        private async void Port_GenerateLoadOrderClicked(object? sender, EventArgs e)
        {
            await PortHandlers.HandleGenerateLoadOrderAsync();
        }

        private async void Port_ExportJsonClicked(object? sender, EventArgs e)
        {
            using var dlg = new SaveFileDialog();
            dlg.Filter = "JSON Files|*.json";
            dlg.DefaultExt = "json";
            dlg.FileName = "mods_load_order.json";
            if (dlg.ShowDialog() != DialogResult.OK) return;

            await PortHandlers.HandleExportJsonAsync(dlg.FileName);
        }

        private async void Port_ExportVortexClicked(object? sender, EventArgs e)
        {
            using var dlg = new SaveFileDialog();
            dlg.Filter = "JSON Files|*.json";
            dlg.DefaultExt = "json";
            dlg.FileName = "Vortex_LoadOrder.json";
            if (dlg.ShowDialog() != DialogResult.OK) return;

            await PortHandlers.HandleExportVortexAsync(dlg.FileName);
        }

        private sealed class WinFormsUiPort : IUiPort
        {
            private readonly MainForm _form;

            public WinFormsUiPort(MainForm form)
            {
                _form = form;
            }

            public string ModsPath => _form.txtModsPath.Text?.Trim() ?? string.Empty;

            public void InvokeOnUi(Action action)
            {
                if (_form.IsDisposed)
                    return;

                if (_form.InvokeRequired)
                {
                    _form.BeginInvoke(action);
                }
                else
                {
                    action();
                }
            }

            public void SetMods(System.Collections.Generic.IReadOnlyList<ModInfo> mods)
            {
                _form._mods.Clear();
                foreach (var m in mods)
                    _form._mods.Add(m);
            }

            public void ShowInfo(string title, string message)
                => MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Information);

            public void ShowWarning(string title, string message)
                => MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Warning);

            public void ShowError(string title, string message)
                => MessageBox.Show(message, title, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
