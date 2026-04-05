using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

using ModManager.Backend.Models;

namespace ModManagerPrototype
{
    /// <summary>
    /// UI-Only Form - Pure interface with placeholder functions for external logic
    /// All button click handlers call placeholder functions that VS Code can implement later
    /// This is a UI-only project with no business logic or file operations
    /// Features a dark theme with black and grey colors
    /// </summary>
    public partial class Form1 : Form
    {
        // External backend hook (VS Code project will set this)
        /// <summary>
        /// Optional external event handler for UI events.
        /// </summary>
        public IUIEventHandler? UIEventHandler { get; set; }

        private static readonly Color HeatmapCritical = Color.FromArgb(220, 60, 60);
        private static readonly Color HeatmapHigh = Color.FromArgb(255, 153, 0);
        private static readonly Color HeatmapLow = Color.FromArgb(255, 215, 0);
        private static readonly Color HeatmapRedundant = Color.FromArgb(65, 105, 225);
        private static readonly Color HeatmapDisabled = Color.FromArgb(140, 140, 140);
        private static readonly Color HeatmapOk = Color.FromArgb(70, 200, 70);

        private readonly Dictionary<Panel, float> _heatmapSegmentFractions = new Dictionary<Panel, float>();
        private readonly Dictionary<Panel, float> _heatmapSegmentTargets = new Dictionary<Panel, float>();
        private readonly List<Panel> _heatmapBarContainers = new List<Panel>();
        private TableLayoutPanel _heatmapTable;
        private System.Windows.Forms.Timer _heatmapAnimTimer;
        private int _heatmapAnimStartTick;

        private Label _backendErrorBanner;

        private readonly Dictionary<Control, (Color normalBack, Color normalFore)> _heatmapOriginalColors = new Dictionary<Control, (Color, Color)>();
        private readonly Dictionary<Control, List<Control>> _heatmapRowGroups = new Dictionary<Control, List<Control>>();

        private TableLayoutPanel _topActionsTable;
        private int _topActionsColumns = -1;

        private Label _topPathLabel;
        private TextBox _topPathTextBox;
        private Button _topPathBrowseButton;

        private Panel _modsSectionHost;
        private FlowLayoutPanel _modsFiltersToolbar;
        private Label _modsFiltersLabel;

        private Panel _modsHeaderPanel;
        private TableLayoutPanel _modsHeaderTable;
        private Label _modsHeaderTitle;
        private FlowLayoutPanel _modsCountersFlow;
        private Label _modsCountValue;
        private Label _enabledCountValue;
        private Label _conflictsCountValue;

        private Label _modsSearchLabel;
        private Panel _modsSearchBorderPanel;
        private Panel _modsSearchInnerPanel;
        private TextBox _modsSearchTextBox;
        private bool _modsSearchHover;
        private bool _modsSearchFocused;

        private Panel _categoryBorderPanel;
        private bool _categoryHover;
        private bool _categoryFocused;

        private Font? _modsGridBoldFont;

        /// <summary>
        /// Initializes the main UI form.
        /// </summary>
        public Form1()
        {
            InitializeComponent();
            ApplyDarkTheme();
            if (comboBoxCategory != null && comboBoxCategory.Items.Count > 0)
            {
                comboBoxCategory.SelectedIndex = 0;
            }

            // Tooltips: show placement reasoning on hover.
            if (dataGridViewMods != null)
            {
                // This grid is designed to use explicit columns (designer + injected analyzer columns).
                // Avoid WinForms auto-generating duplicate columns on bind.
                dataGridViewMods.AutoGenerateColumns = false;

                dataGridViewMods.ShowCellToolTips = true;
                dataGridViewMods.CellToolTipTextNeeded -= DataGridViewMods_CellToolTipTextNeeded;
                dataGridViewMods.CellToolTipTextNeeded += DataGridViewMods_CellToolTipTextNeeded;

                dataGridViewMods.CellFormatting -= DataGridViewMods_CellFormatting;
                dataGridViewMods.CellFormatting += DataGridViewMods_CellFormatting;

                dataGridViewMods.RowPrePaint -= DataGridViewMods_RowPrePaint;
                dataGridViewMods.RowPrePaint += DataGridViewMods_RowPrePaint;

                dataGridViewMods.DataBindingComplete -= DataGridViewMods_DataBindingComplete;
                dataGridViewMods.DataBindingComplete += DataGridViewMods_DataBindingComplete;

                // If/when the grid is data-bound, ensure Tier is bound to ResolvedTier.
                if (columnTier != null)
                    columnTier.DataPropertyName = nameof(ModInfo.ResolvedTier);

                // Bind the rest of the designer columns when/if data-binding is used.
                BindModsGridDesignerColumns();

                // Add/bind Confidence column (UI only; safe even if data-binding happens later).
                EnsureConfidenceColumn();

                // Analyzer diagnostics columns (UI only; safe even if data-binding happens later).
                EnsureAnalyzerColumns(dataGridViewMods);
            }
        }

        internal string GetModsPath()
        {
            try
            {
                return _topPathTextBox?.Text ?? string.Empty;
            }
            catch
            {
                return string.Empty;
            }
        }

        private void DataGridViewMods_DataBindingComplete(object? sender, DataGridViewBindingCompleteEventArgs e)
        {
            if (dataGridViewMods == null)
                return;

            // Ensure columns after binding (correct + resilient).
            if (columnTier != null)
                columnTier.DataPropertyName = nameof(ModInfo.ResolvedTier);

            BindModsGridDesignerColumns();

            EnsureConfidenceColumn();
            EnsureAnalyzerColumns(dataGridViewMods);
        }

        private void BindModsGridDesignerColumns()
        {
            if (dataGridViewMods == null)
                return;

            if (columnEnabled != null)
                columnEnabled.DataPropertyName = nameof(ModInfo.Enabled);
            if (columnModName != null)
                columnModName.DataPropertyName = nameof(ModInfo.Name);
            if (columnCategory != null)
                columnCategory.DataPropertyName = nameof(ModInfo.Category);
            if (columnStatus != null)
                columnStatus.DataPropertyName = nameof(ModInfo.Status);

            // columnSuggestedAction intentionally left unbound (backend may compute this later).
        }

        private void SetModsDataSource(object? dataSource)
        {
            if (dataGridViewMods == null)
                return;

            dataGridViewMods.SuspendLayout();
            try
            {
                dataGridViewMods.DataSource = null;
                dataGridViewMods.DataSource = dataSource;

                // Deterministic injection immediately after binding.
                if (columnTier != null)
                    columnTier.DataPropertyName = nameof(ModInfo.ResolvedTier);
                BindModsGridDesignerColumns();
                EnsureConfidenceColumn();
                EnsureAnalyzerColumns(dataGridViewMods);
            }
            finally
            {
                dataGridViewMods.ResumeLayout();
            }
        }

        private void EnsureConfidenceColumn()
        {
            if (dataGridViewMods == null)
                return;

            const string name = "columnConfidence";
            if (dataGridViewMods.Columns.Contains(name))
            {
                dataGridViewMods.Columns[name].DataPropertyName = nameof(ModInfo.PlacementConfidence);
                return;
            }

            var col = new DataGridViewTextBoxColumn
            {
                Name = name,
                HeaderText = "Confidence",
                DataPropertyName = nameof(ModInfo.PlacementConfidence),
                Width = 90,
                ReadOnly = true
            };
            col.DefaultCellStyle.Format = "0'%'";

            var tierIndex = columnTier != null ? columnTier.Index : -1;
            if (tierIndex >= 0 && tierIndex < dataGridViewMods.Columns.Count - 1)
                dataGridViewMods.Columns.Insert(tierIndex + 1, col);
            else
                dataGridViewMods.Columns.Add(col);
        }

        private static void EnsureAnalyzerColumns(DataGridView grid)
        {
            if (grid == null)
                return;

            // Keep these adjacent to the Tier/Confidence columns for quick scanning.
            var insertAt = -1;
            if (grid.Columns.Contains("columnConfidence"))
                insertAt = grid.Columns["columnConfidence"].Index + 1;
            else if (grid.Columns.Contains("columnTier"))
                insertAt = grid.Columns["columnTier"].Index + 1;

            void InsertOrAdd(DataGridViewColumn column)
            {
                if (grid.Columns.Contains(column.Name))
                    return;

                if (insertAt >= 0 && insertAt <= grid.Columns.Count)
                {
                    grid.Columns.Insert(insertAt, column);
                    insertAt++;
                }
                else
                {
                    grid.Columns.Add(column);
                }
            }

            // UI override diagnostics
            if (grid.Columns.Contains("IsUiOverride"))
                grid.Columns["IsUiOverride"].DataPropertyName = nameof(ModInfo.IsUiOverride);
            else
                InsertOrAdd(new DataGridViewCheckBoxColumn
                {
                    Name = "IsUiOverride",
                    HeaderText = "UI Override?",
                    DataPropertyName = nameof(ModInfo.IsUiOverride),
                    ReadOnly = true,
                    Width = 90
                });

            if (grid.Columns.Contains("UiOverrideRank"))
                grid.Columns["UiOverrideRank"].DataPropertyName = nameof(ModInfo.UiOverrideRank);
            else
                InsertOrAdd(new DataGridViewTextBoxColumn
                {
                    Name = "UiOverrideRank",
                    HeaderText = "UI Override Rank",
                    DataPropertyName = nameof(ModInfo.UiOverrideRank),
                    ReadOnly = true,
                    Width = 110
                });

            if (grid.Columns.Contains("Conflict"))
                grid.Columns["Conflict"].DataPropertyName = nameof(ModInfo.HasConflict);
            else
                InsertOrAdd(new DataGridViewCheckBoxColumn
                {
                    Name = "Conflict",
                    HeaderText = "Conflict",
                    DataPropertyName = nameof(ModInfo.HasConflict),
                    ReadOnly = true,
                    Width = 70
                });

            if (grid.Columns.Contains("XPathOverlap"))
                grid.Columns["XPathOverlap"].DataPropertyName = nameof(ModInfo.XPathOverlapCount);
            else
                InsertOrAdd(new DataGridViewTextBoxColumn
                {
                    Name = "XPathOverlap",
                    HeaderText = "XPath Overlap",
                    DataPropertyName = nameof(ModInfo.XPathOverlapCount),
                    ReadOnly = true,
                    Width = 90
                });

            if (grid.Columns.Contains("Impact"))
                grid.Columns["Impact"].DataPropertyName = nameof(ModInfo.LoadImpactScore);
            else
            {
                var col = new DataGridViewTextBoxColumn
                {
                    Name = "Impact",
                    HeaderText = "Impact",
                    DataPropertyName = nameof(ModInfo.LoadImpactScore),
                    ReadOnly = true,
                    Width = 75
                };
                col.DefaultCellStyle.Format = "0'%'";
                InsertOrAdd(col);
            }

            if (!grid.Columns.Contains("MissingDeps"))
                InsertOrAdd(new DataGridViewTextBoxColumn
                {
                    Name = "MissingDeps",
                    HeaderText = "Missing Deps",
                    ReadOnly = true,
                    Width = 150
                });
        }

        private void DataGridViewMods_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
        {
            if (e.RowIndex < 0)
                return;

            var grid = sender as DataGridView;
            if (grid == null)
                return;

            if (grid.Columns[e.ColumnIndex].Name == "MissingDeps")
            {
                var mod = grid.Rows[e.RowIndex].DataBoundItem as ModInfo;
                if (mod == null)
                    return;

                e.Value = (mod.MissingDependencies != null && mod.MissingDependencies.Any())
                    ? string.Join(", ", mod.MissingDependencies)
                    : "";

                e.FormattingApplied = true;
            }
        }

        private void DataGridViewMods_RowPrePaint(object? sender, DataGridViewRowPrePaintEventArgs e)
        {
            var grid = sender as DataGridView;
            if (grid == null)
                return;

            if (e.RowIndex < 0)
                return;

            var row = grid.Rows[e.RowIndex];
            var mod = row.DataBoundItem as ModInfo;
            if (mod == null)
                return;

            // Always reset first (critical)
            row.DefaultCellStyle.BackColor = grid.DefaultCellStyle.BackColor;
            row.DefaultCellStyle.ForeColor = grid.DefaultCellStyle.ForeColor;
            row.DefaultCellStyle.Font = grid.Font;

            // Severity coloring (row-level, conflict wins)
            if (mod.HasConflict)
                row.DefaultCellStyle.BackColor = Color.MistyRose;
            else if (mod.MissingDependencies != null && mod.MissingDependencies.Any())
                row.DefaultCellStyle.BackColor = Color.LightYellow;

            // UI overrides: visually emphasize (bold always; color when not already severity-colored)
            if (mod.IsUiOverride)
            {
                if (_modsGridBoldFont == null || _modsGridBoldFont.FontFamily.Name != grid.Font.FontFamily.Name || Math.Abs(_modsGridBoldFont.Size - grid.Font.Size) > 0.01f)
                    _modsGridBoldFont = new Font(grid.Font, FontStyle.Bold);

                row.DefaultCellStyle.Font = _modsGridBoldFont;

                if (!mod.HasConflict && (mod.MissingDependencies == null || !mod.MissingDependencies.Any()))
                    row.DefaultCellStyle.BackColor = Color.LightGoldenrodYellow;
            }
        }

        private void DataGridViewMods_CellToolTipTextNeeded(object? sender, DataGridViewCellToolTipTextNeededEventArgs e)
        {
            if (e.RowIndex < 0)
                return;

            if (dataGridViewMods == null)
                return;

            var mod = dataGridViewMods.Rows[e.RowIndex].DataBoundItem as ModInfo;
            if (mod == null)
                return;

            e.ToolTipText = mod.LoadReason ?? string.Empty;
        }

        private void SendPort(int port, object? data = null)
        {
            UIEventHandler?.HandleUIEvent(new PortData
            {
                Port = port,
                Data = data
            });
        }

        /// <summary>
        /// Backend → UI entry point for renderer-only snapshot updates.
        /// Backend must pass a fully constructed snapshot object via PortData.Data.
        /// </summary>
        public void HandleUIEvent(PortData eventData)
        {
            var snapshot = eventData?.Data as BackendSnapshot;
            if (snapshot == null)
                return;

            if (InvokeRequired)
            {
                BeginInvoke((Action)(() => RenderSnapshot(snapshot)));
                return;
            }

            RenderSnapshot(snapshot);
        }

        private static void MoveControlTo(Control c, Control newParent)
        {
            if (c == null || newParent == null)
                return;

            if (c.Parent != null)
                c.Parent.Controls.Remove(c);

            newParent.Controls.Add(c);
        }

        private Button[] GetTopActionButtons()
        {
            return new[]
            {
                buttonScanMods,
                buttonGenerateApplyLoadOrder,
                buttonExportLoadOrder,
                buttonRenameFolder,
                buttonExplainIssues,
                buttonResolveConflicts,
                buttonFindDuplicates,
                buttonApplyUpdateFixes,
                buttonExplainSelected,
                buttonDiagnoseVisibility
            };
        }

        private void Port_FormLoaded()
        {
            // UI → Backend port: form loaded
            SendPort(PortContract.FORM_LOADED);
        }

        private void Port_ScanModsClicked()
        {
            SendPort(PortContract.SCAN_MODS);
        }

        private void Port_GenerateLoadOrderClicked()
        {
            SendPort(PortContract.GENERATE_APPLY_LOAD_ORDER);
        }

        private void Port_ExportLoadOrderClicked()
        {
            SendPort(PortContract.EXPORT_LOAD_ORDER);
        }

        private void Port_RenameFolderClicked()
        {
            SendPort(PortContract.RENAME_FOLDER);
        }

        private void Port_ExplainIssuesClicked()
        {
            SendPort(PortContract.EXPLAIN_ISSUES);
        }

        private void Port_ResolveConflictsClicked()
        {
            SendPort(PortContract.RESOLVE_CONFLICTS);
        }

        private void Port_FindDuplicatesClicked()
        {
            SendPort(PortContract.FIND_DUPLICATES);
        }

        private void Port_ApplyUpdateFixesClicked()
        {
            SendPort(PortContract.APPLY_UPDATE_FIXES);
        }

        private void Port_ExplainSelectedClicked()
        {
            SendPort(PortContract.EXPLAIN_SELECTED);
        }

        private void Port_DiagnoseVisibilityClicked()
        {
            SendPort(PortContract.DIAGNOSE_VISIBILITY);
        }

        private void Port_FilterCriticalClicked()
        {
            SendPort(PortContract.FILTER_CRITICAL);
        }

        private void Port_FilterHighClicked()
        {
            SendPort(PortContract.FILTER_HIGH);
        }

        private void Port_FilterLowClicked()
        {
            SendPort(PortContract.FILTER_LOW);
        }

        private void Port_FilterRedundantClicked()
        {
            SendPort(PortContract.FILTER_REDUNDANT);
        }

        private void Port_FilterDisabledClicked()
        {
            SendPort(PortContract.FILTER_DISABLED);
        }

        private void Port_FilterOkClicked()
        {
            SendPort(PortContract.FILTER_OK);
        }

        private void Port_CategoryChanged()
        {
            SendPort(PortContract.FILTER_CATEGORY_CHANGED, comboBoxCategory?.SelectedItem);
        }

        private void Port_SeverityChanged()
        {
            SendPort(PortContract.FILTER_SEVERITY_CHANGED, trackBarSeverity?.Value);
        }

        private void Port_ConflictsOnlyChanged()
        {
            SendPort(PortContract.FILTER_CONFLICTS_ONLY_CHANGED, checkBoxConflictsOnly?.Checked);
        }

        private void Port_ShowAllChanged()
        {
            SendPort(PortContract.FILTER_SHOW_ALL_CHANGED, checkBoxShowAll?.Checked);
        }

        private void Port_SearchTextChanged(string text)
        {
            SendPort(PortContract.FILTER_SEARCH_TEXT_CHANGED, text);
        }

        private void Port_HeatmapCellClicked(string modName)
        {
            SendPort(PortContract.HEATMAP_CELL_CLICKED, modName);
        }

        /// <summary>
        /// Applies dark theme to all UI controls
        /// Black and grey color scheme for modern dark theme appearance
        /// </summary>
        private void ApplyDarkTheme()
        {
            // Form background and text
            this.BackColor = Color.FromArgb(32, 32, 32); // Dark grey
            this.ForeColor = Color.LightGray;

            tableMain.BackColor = Color.FromArgb(32, 32, 32);
            panelTop.BackColor = Color.FromArgb(40, 40, 40);
            tableTop.BackColor = Color.FromArgb(40, 40, 40);
            flowTopActions.BackColor = Color.FromArgb(40, 40, 40);
            flowControlFilters.BackColor = Color.FromArgb(40, 40, 40);
            panelSpacer.BackColor = Color.FromArgb(32, 32, 32);
            flowLegend.BackColor = Color.FromArgb(32, 32, 32);

            groupBoxHeatmap.BackColor = Color.FromArgb(32, 32, 32);
            groupBoxHeatmap.ForeColor = Color.LightGray;
            panelHeatmapScroll.BackColor = Color.FromArgb(25, 25, 25);
            flowHeatmap.BackColor = Color.FromArgb(25, 25, 25);

            if (groupBoxMods != null)
            {
                groupBoxMods.BackColor = Color.FromArgb(32, 32, 32);
                groupBoxMods.ForeColor = Color.LightGray;
            }

            if (dataGridViewMods != null)
            {
                dataGridViewMods.BackgroundColor = Color.FromArgb(25, 25, 25);
                dataGridViewMods.GridColor = Color.FromArgb(64, 64, 64);
                dataGridViewMods.BorderStyle = BorderStyle.None;
                dataGridViewMods.EnableHeadersVisualStyles = false;

                dataGridViewMods.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(45, 45, 45);
                dataGridViewMods.ColumnHeadersDefaultCellStyle.ForeColor = Color.White;
                dataGridViewMods.DefaultCellStyle.BackColor = Color.FromArgb(25, 25, 25);
                dataGridViewMods.DefaultCellStyle.ForeColor = Color.LightGray;
                dataGridViewMods.DefaultCellStyle.SelectionBackColor = Color.FromArgb(70, 70, 70);
                dataGridViewMods.DefaultCellStyle.SelectionForeColor = Color.White;
            }

            labelStats.ForeColor = Color.LightGray;
            labelCategory.ForeColor = Color.LightGray;
            labelSeverity.ForeColor = Color.LightGray;

            comboBoxCategory.BackColor = Color.FromArgb(25, 25, 25);
            comboBoxCategory.ForeColor = Color.LightGray;
            comboBoxCategory.FlatStyle = FlatStyle.Flat;

            trackBarSeverity.BackColor = Color.FromArgb(40, 40, 40);

            checkBoxConflictsOnly.ForeColor = Color.LightGray;
            checkBoxConflictsOnly.BackColor = Color.FromArgb(40, 40, 40);

            checkBoxShowAll.ForeColor = Color.LightGray;
            checkBoxShowAll.BackColor = Color.FromArgb(40, 40, 40);

            legendCritical.ForeColor = Color.LightGray;
            legendHigh.ForeColor = Color.LightGray;
            legendLow.ForeColor = Color.LightGray;
            legendRedundant.ForeColor = Color.LightGray;
            legendDisabled.ForeColor = Color.LightGray;
            legendOk.ForeColor = Color.LightGray;

            // Apply dark theme to all buttons
            ApplyDarkThemeToButtons();
        }

        /// <summary>
        /// Applies dark theme styling to all buttons
        /// Black and grey hover effects for modern appearance
        /// </summary>
        private void ApplyDarkThemeToButtons()
        {
            SetButtonDarkTheme(buttonScanMods, "Scan Mods");
            SetButtonDarkTheme(buttonGenerateApplyLoadOrder, "Generate + Apply Load Order");
            SetButtonDarkTheme(buttonExportLoadOrder, "Export Load Order");
            SetButtonDarkTheme(buttonRenameFolder, "Rename Folder");
            SetButtonDarkTheme(buttonExplainIssues, "Explain Issues");
            SetButtonDarkTheme(buttonResolveConflicts, "Resolve Conflicts");
            SetButtonDarkTheme(buttonFindDuplicates, "Find Duplicates");
            SetButtonDarkTheme(buttonApplyUpdateFixes, "Apply Update Fixes");
            SetButtonDarkTheme(buttonExplainSelected, "Explain Selected");
            SetButtonDarkTheme(buttonDiagnoseVisibility, "Diagnose Visibility");

            SetButtonDarkTheme(buttonFilterCritical, "Filter Critical");
            SetButtonDarkTheme(buttonFilterHigh, "Filter High");
            SetButtonDarkTheme(buttonFilterLow, "Filter Low");
            SetButtonDarkTheme(buttonFilterRedundant, "Filter Redundant");
            SetButtonDarkTheme(buttonFilterDisabled, "Filter Disabled");
            SetButtonDarkTheme(buttonFilterOK, "Filter OK");
        }

        /// <summary>
        /// Sets dark theme styling for a single button
        /// </summary>
        private void SetButtonDarkTheme(Button button, string toolTip)
        {
            if (button == null)
                return;

            button.AutoSize = false;
            int minW = button.MinimumSize.Width;
            if (minW <= 0)
                minW = 90;

            button.MinimumSize = new Size(minW, 40);
            button.Height = 40;
            button.Padding = new Padding(6, 3, 6, 3);
            button.Margin = new Padding(6, 6, 6, 6);
            button.TextAlign = ContentAlignment.MiddleCenter;
            button.UseCompatibleTextRendering = true;
            button.AutoEllipsis = true;

            button.BackColor = Color.FromArgb(64, 64, 64); // Medium grey
            button.ForeColor = Color.White;
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 1;
            button.FlatAppearance.BorderColor = Color.FromArgb(80, 80, 80);
            button.Font = new Font("Segoe UI", 9F, FontStyle.Regular);

            // Add hover effects
            button.MouseEnter += (sender, e) =>
            {
                button.BackColor = Color.FromArgb(80, 80, 80); // Lighter grey on hover
                button.Cursor = Cursors.Hand;
            };

            button.MouseLeave += (sender, e) =>
            {
                button.BackColor = Color.FromArgb(64, 64, 64); // Return to normal
                button.Cursor = Cursors.Default;
            };

            // Add click effect
            button.MouseDown += (sender, e) =>
            {
                button.BackColor = Color.FromArgb(96, 96, 96); // Darker on click
            };

            button.MouseUp += (sender, e) =>
            {
                button.BackColor = Color.FromArgb(80, 80, 80); // Return to hover color
            };
        }

        #region Button Click Handlers - UI Ports for External Logic

        /// <summary>
        /// Port: Select Mods Folder Button
        /// UI Event Handler - External logic will be attached here by VS Code
        /// Purpose: Open folder browser and let external code handle folder selection
        /// </summary>
        private void buttonScanMods_Click(object sender, EventArgs e)
        {
            Port_ScanModsClicked();
        }

        private void buttonGenerateApplyLoadOrder_Click(object sender, EventArgs e)
        {
            Port_GenerateLoadOrderClicked();
        }

        private void buttonExportLoadOrder_Click(object sender, EventArgs e)
        {
            Port_ExportLoadOrderClicked();
        }

        private void buttonRenameFolder_Click(object sender, EventArgs e)
        {
            Port_RenameFolderClicked();
        }

        private void buttonExplainIssues_Click(object sender, EventArgs e)
        {
            Port_ExplainIssuesClicked();
        }

        private void buttonResolveConflicts_Click(object sender, EventArgs e)
        {
            Port_ResolveConflictsClicked();
        }

        private void buttonFindDuplicates_Click(object sender, EventArgs e)
        {
            Port_FindDuplicatesClicked();
        }

        private void buttonApplyUpdateFixes_Click(object sender, EventArgs e)
        {
            Port_ApplyUpdateFixesClicked();
        }

        private void buttonExplainSelected_Click(object sender, EventArgs e)
        {
            Port_ExplainSelectedClicked();
        }

        private void buttonDiagnoseVisibility_Click(object sender, EventArgs e)
        {
            Port_DiagnoseVisibilityClicked();
        }

        #endregion
        private void buttonFilterCritical_Click(object sender, EventArgs e)
        {
            Port_FilterCriticalClicked();
        }

        private void buttonFilterHigh_Click(object sender, EventArgs e)
        {
            Port_FilterHighClicked();
        }

        private void buttonFilterLow_Click(object sender, EventArgs e)
        {
            Port_FilterLowClicked();
        }

        private void buttonFilterRedundant_Click(object sender, EventArgs e)
        {
            Port_FilterRedundantClicked();
        }

        private void buttonFilterDisabled_Click(object sender, EventArgs e)
        {
            Port_FilterDisabledClicked();
        }

        private void buttonFilterOK_Click(object sender, EventArgs e)
        {
            Port_FilterOkClicked();
        }

        private void comboBoxCategory_SelectedIndexChanged(object sender, EventArgs e)
        {
            Port_CategoryChanged();
        }

        private void trackBarSeverity_ValueChanged(object sender, EventArgs e)
        {
            Port_SeverityChanged();
        }

        private void checkBoxConflictsOnly_CheckedChanged(object sender, EventArgs e)
        {
            Port_ConflictsOnlyChanged();
        }

        private void checkBoxShowAll_CheckedChanged(object sender, EventArgs e)
        {
            Port_ShowAllChanged();
        }

        private void flowHeatmap_ControlAdded(object sender, ControlEventArgs e)
        {
            if (e?.Control == null)
                return;

            e.Control.Margin = new Padding(4);
            e.Control.Padding = new Padding(4);
            e.Control.BackColor = Color.FromArgb(64, 64, 64);
            e.Control.ForeColor = Color.White;
            e.Control.Cursor = Cursors.Hand;

            toolTipHeatmap.SetToolTip(e.Control, "Heatmap cell");

            e.Control.Click += HeatmapCell_Click;
        }

        private void HeatmapCell_Click(object sender, EventArgs e)
        {
            if (sender is Control c)
            {
                var name = c.Tag as string;
                if (string.IsNullOrWhiteSpace(name))
                    name = c.Text;

                Port_HeatmapCellClicked(name);
            }
        }

        private void Form1_Load(object sender, EventArgs e)
        {
            Port_FormLoaded();

            // Ensure top UI is interactive and not blocked by any overlapping docked panels
            if (panelTop != null)
            {
                panelTop.Visible = true;
                panelTop.Enabled = true;
                panelTop.BringToFront();
            }

            if (tableMain != null)
            {
                tableMain.Visible = true;
                tableMain.Enabled = true;
                tableMain.BringToFront();
            }

            if (groupBoxHeatmap != null)
            {
                groupBoxHeatmap.Visible = true;
                groupBoxHeatmap.Enabled = true;
            }

            NormalizeLayout();
            EnsureTopActionButtonTable();
            EnsureFiltersRow();
            EnsureModsFiltersToolbar();
            PopulateCategoryDropdown();
            BuildLegend();
            EnsureErrorBanner();
            RenderHeatmapEmptyState();

            // Request the latest backend snapshot (authoritative UI render path).
            SendPort(PortContract.PortIds.GetBackendSnapshot);

#if DEBUG
            // Debug-only fallback: if no backend is wired, show sample data.
            if (UIEventHandler == null)
                TestHeatmapWithSampleSnapshot();
#endif
        }

        private void TestHeatmapWithSampleSnapshot()
        {
            var sample = new BackendSnapshot
            {
                Categories = new List<CategorySnapshot>
                {
                    new CategorySnapshot
                    {
                        Category = "Gameplay",
                        TotalMods = 12,
                        Percentages = new Dictionary<string, double>
                        {
                            { "Critical", 16.7 },
                            { "High", 25.0 },
                            { "Low", 8.3 },
                            { "Redundant", 16.7 },
                            { "Disabled", 8.3 },
                            { "OK", 25.0 }
                        }
                    },
                    new CategorySnapshot
                    {
                        Category = "Overhauls",
                        TotalMods = 8,
                        Percentages = new Dictionary<string, double>
                        {
                            { "Critical", 0.0 },
                            { "High", 12.5 },
                            { "Low", 25.0 },
                            { "Redundant", 0.0 },
                            { "Disabled", 0.0 },
                            { "OK", 62.5 }
                        }
                    },
                    new CategorySnapshot
                    {
                        Category = "Visual / Audio",
                        TotalMods = 5,
                        Percentages = new Dictionary<string, double>
                        {
                            { "Critical", 0.0 },
                            { "High", 0.0 },
                            { "Low", 0.0 },
                            { "Redundant", 0.0 },
                            { "Disabled", 20.0 },
                            { "OK", 80.0 }
                        }
                    }
                },
                Totals = new TotalsSnapshot
                {
                    Mods = 25,
                    Enabled = 20,
                    Disabled = 5,
                    Conflicts = 3
                },
                Meta = new MetaSnapshot
                {
                    GeneratedAt = DateTime.UtcNow.ToString("O"),
                    ScanDurationMs = 42
                },
                Mods = new List<ModInfo>
                {
                    new ModInfo
                    {
                        Id = "corelib",
                        Name = "0-CoreLib",
                        Enabled = true,
                        Category = "Core",
                        Status = "OK",
                        ResolvedTier = ModTier.Core,
                        PlacementConfidence = 95,
                        HasConflict = false,
                        XPathOverlapCount = 0,
                        LoadImpactScore = 30,
                        LoadReason = "Core framework detected; loads first."
                    },
                    new ModInfo
                    {
                        Id = "uihud",
                        Name = "UI-HUD",
                        Enabled = true,
                        Category = "UI",
                        Status = "Warning",
                        ResolvedTier = ModTier.UI,
                        PlacementConfidence = 85,
                        HasConflict = true,
                        XPathOverlapCount = 3,
                        LoadImpactScore = 60,
                        MissingDependencies = new List<string> { "SomeMissingMod" },
                        LoadReason = "UI files + XPath edits detected; placed late. XPath overlaps found."
                    },
                    new ModInfo
                    {
                        Id = "patch",
                        Name = "Z-Patch-Compat",
                        Enabled = true,
                        Category = "Patch",
                        Status = "OK",
                        ResolvedTier = ModTier.Patch,
                        PlacementConfidence = 75,
                        HasConflict = false,
                        XPathOverlapCount = 1,
                        LoadImpactScore = 10,
                        LoadReason = "Small patch mod; loads last."
                    }
                },
                Error = null
            };

            // Simulate backend delivering the snapshot
            HandleUIEvent(new PortData { Data = sample });
        }

        private void EnsureErrorBanner()
        {
            if (_backendErrorBanner != null || groupBoxHeatmap == null)
                return;

            _backendErrorBanner = new Label
            {
                Dock = DockStyle.Top,
                AutoSize = false,
                Height = 0,
                Visible = false,
                ForeColor = Color.FromArgb(255, 210, 210),
                BackColor = Color.FromArgb(55, 25, 25),
                Padding = new Padding(8, 6, 8, 6),
                TextAlign = ContentAlignment.MiddleLeft
            };

            groupBoxHeatmap.Controls.Add(_backendErrorBanner);
            groupBoxHeatmap.Controls.SetChildIndex(_backendErrorBanner, 0);
        }

        private void RenderSnapshot(BackendSnapshot snapshot)
        {
            EnsureErrorBanner();

            RenderError(snapshot?.Error);
            RenderTotals(snapshot?.Totals);
            RenderHeatmap(snapshot?.Categories);
            RenderMods(snapshot?.Mods);
        }

        private void RenderMods(IReadOnlyList<ModInfo>? mods)
        {
            if (mods == null)
                return;

            // UI-only ordering for inspection: UI overrides first, then by override rank (desc).
            // This does not mutate backend state.
            var view = new List<ModInfo>(mods);
            view.Sort((a, b) =>
            {
                var aOverride = a != null && a.IsUiOverride;
                var bOverride = b != null && b.IsUiOverride;

                var c = bOverride.CompareTo(aOverride);
                if (c != 0) return c;

                var aRank = a?.UiOverrideRank ?? 0;
                var bRank = b?.UiOverrideRank ?? 0;
                c = bRank.CompareTo(aRank);
                if (c != 0) return c;

                var aOrder = a?.LoadOrder ?? int.MaxValue;
                var bOrder = b?.LoadOrder ?? int.MaxValue;
                c = aOrder.CompareTo(bOrder);
                if (c != 0) return c;

                return string.Compare(a?.Name ?? string.Empty, b?.Name ?? string.Empty, StringComparison.OrdinalIgnoreCase);
            });

            SetModsDataSource(view);
        }

        private void RenderError(ErrorSnapshot err)
        {
            if (_backendErrorBanner == null)
                return;

            if (err == null)
            {
                _backendErrorBanner.Visible = false;
                _backendErrorBanner.Height = 0;
                _backendErrorBanner.Text = string.Empty;
                return;
            }

            var msg = err.Message ?? "";
            var code = err.Code ?? "";
            var details = err.Details ?? "";

            string text = string.IsNullOrWhiteSpace(code) ? msg : (code + ": " + msg);
            if (!string.IsNullOrWhiteSpace(details))
                text += "  " + details;

            _backendErrorBanner.Text = text;
            _backendErrorBanner.Visible = true;
            _backendErrorBanner.Height = 34;
        }

        private void RenderTotals(TotalsSnapshot totals)
        {
            if (totals == null)
                return;

            if (_modsCountValue != null)
                _modsCountValue.Text = totals.Mods.ToString();
            if (_enabledCountValue != null)
                _enabledCountValue.Text = totals.Enabled.ToString();
            if (_conflictsCountValue != null)
                _conflictsCountValue.Text = totals.Conflicts.ToString();
        }

        private void ComboBoxCategory_DropDown(object sender, EventArgs e)
        {
            EnsureCategoryDropdownSorted();
        }

        private void EnsureModsFiltersToolbar()
        {
            if (groupBoxMods == null || dataGridViewMods == null)
                return;

            if (_modsSectionHost == null)
            {
                _modsSectionHost = new Panel
                {
                    Dock = DockStyle.Fill,
                    Margin = new Padding(0),
                    Padding = new Padding(0)
                };

                if (groupBoxMods.Controls.Contains(dataGridViewMods))
                    groupBoxMods.Controls.Remove(dataGridViewMods);

                groupBoxMods.Controls.Add(_modsSectionHost);
                _modsSectionHost.Controls.Add(dataGridViewMods);
            }

            EnsureModsHeader();

            if (_modsFiltersToolbar == null)
            {
                _modsFiltersToolbar = new FlowLayoutPanel
                {
                    Dock = DockStyle.Top,
                    AutoSize = true,
                    AutoSizeMode = AutoSizeMode.GrowAndShrink,
                    Padding = new Padding(6, 4, 6, 4),
                    Margin = new Padding(0),
                    FlowDirection = FlowDirection.LeftToRight,
                    WrapContents = true,
                    AutoScroll = false
                };

                _modsFiltersToolbar.HorizontalScroll.Enabled = false;
                _modsFiltersToolbar.HorizontalScroll.Visible = false;

                _modsFiltersLabel = new Label
                {
                    AutoSize = true,
                    Text = "Mods Filters",
                    ForeColor = Color.LightGray,
                    Font = new Font("Segoe UI", 9F, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Margin = new Padding(0, 6, 10, 4)
                };

                _modsFiltersToolbar.Controls.Add(_modsFiltersLabel);
                _modsSectionHost.Controls.Add(_modsFiltersToolbar);
                _modsSectionHost.Controls.SetChildIndex(_modsFiltersToolbar, 0);
            }

            EnsureModsSearchBoxChrome();

            var controlsToMove = new Control[]
            {
                labelCategory,
                comboBoxCategory,
                labelSeverity,
                trackBarSeverity,
                checkBoxConflictsOnly,
                checkBoxShowAll
            };

            foreach (var c in controlsToMove)
            {
                if (c == null)
                    continue;

                if (c.Parent != null)
                    c.Parent.Controls.Remove(c);
            }

            // Ensure the order matches the requested toolbar layout.
            AddToModsToolbar(labelCategory);
            AddToModsToolbar(comboBoxCategory);
            AddToModsToolbar(labelSeverity);
            AddToModsToolbar(trackBarSeverity);
            AddToModsToolbar(checkBoxConflictsOnly);
            AddToModsToolbar(checkBoxShowAll);

            if (comboBoxCategory != null)
            {
                comboBoxCategory.Width = 180;
                comboBoxCategory.Anchor = AnchorStyles.Left;
                comboBoxCategory.Margin = new Padding(0);

                EnsureCategoryDropdownChrome();
            }

            if (trackBarSeverity != null)
            {
                trackBarSeverity.Width = 140;
                trackBarSeverity.TickStyle = TickStyle.None;
                trackBarSeverity.AutoSize = false;
                trackBarSeverity.Height = 28;
                trackBarSeverity.Margin = new Padding(0, 4, 10, 4);
            }

            if (checkBoxConflictsOnly != null)
            {
                checkBoxConflictsOnly.AutoSize = true;
                checkBoxConflictsOnly.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
                checkBoxConflictsOnly.Margin = new Padding(0, 6, 10, 4);
            }

            if (checkBoxShowAll != null)
            {
                checkBoxShowAll.AutoSize = true;
                checkBoxShowAll.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
                checkBoxShowAll.Margin = new Padding(0, 6, 10, 4);
            }

            if (labelCategory != null)
            {
                labelCategory.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
                labelCategory.Margin = new Padding(0, 6, 6, 4);
                labelCategory.TextAlign = ContentAlignment.MiddleLeft;
            }

            if (labelSeverity != null)
            {
                labelSeverity.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
                labelSeverity.Margin = new Padding(0, 6, 6, 4);
                labelSeverity.TextAlign = ContentAlignment.MiddleLeft;
            }

            dataGridViewMods.Dock = DockStyle.Fill;
        }

        private void EnsureTopPathRow()
        {
            // No longer used; path controls are now created inline in the header via EnsureTopPathRowInHeader.
        }

        private void TopPathBrowseButton_Click(object sender, EventArgs e)
        {
            SendPort(PortContract.SELECT_FOLDER);
        }

        private void EnsureModsSearchBoxChrome()
        {
            if (_modsFiltersToolbar == null)
                return;

            if (_modsSearchLabel == null)
            {
                _modsSearchLabel = new Label
                {
                    AutoSize = true,
                    Text = "Search:",
                    ForeColor = Color.LightGray,
                    Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Margin = new Padding(0, 6, 6, 4)
                };
            }

            if (_modsSearchBorderPanel == null)
            {
                _modsSearchBorderPanel = new Panel
                {
                    Width = 240,
                    Height = 28,
                    Padding = new Padding(1),
                    Margin = new Padding(0, 4, 10, 4),
                    BackColor = Color.FromArgb(90, 90, 90)
                };

                _modsSearchInnerPanel = new Panel
                {
                    Dock = DockStyle.Fill,
                    BackColor = Color.FromArgb(35, 35, 35),
                    Padding = new Padding(6, 5, 6, 5)
                };

                _modsSearchTextBox = new TextBox
                {
                    BorderStyle = BorderStyle.None,
                    Dock = DockStyle.Fill,
                    ForeColor = Color.LightGray,
                    BackColor = Color.FromArgb(35, 35, 35),
                    Font = new Font("Segoe UI", 9F, FontStyle.Regular)
                };

                _modsSearchTextBox.TextChanged -= ModsSearchTextBox_TextChanged;
                _modsSearchTextBox.TextChanged += ModsSearchTextBox_TextChanged;
                _modsSearchTextBox.MouseEnter -= ModsSearchTextBox_MouseEnter;
                _modsSearchTextBox.MouseEnter += ModsSearchTextBox_MouseEnter;
                _modsSearchTextBox.MouseLeave -= ModsSearchTextBox_MouseLeave;
                _modsSearchTextBox.MouseLeave += ModsSearchTextBox_MouseLeave;
                _modsSearchTextBox.Enter -= ModsSearchTextBox_Enter;
                _modsSearchTextBox.Enter += ModsSearchTextBox_Enter;
                _modsSearchTextBox.Leave -= ModsSearchTextBox_Leave;
                _modsSearchTextBox.Leave += ModsSearchTextBox_Leave;

                _modsSearchInnerPanel.Controls.Add(_modsSearchTextBox);
                _modsSearchBorderPanel.Controls.Add(_modsSearchInnerPanel);

                UpdateModsSearchBorderColor();
            }

            if (!_modsFiltersToolbar.Controls.Contains(_modsSearchLabel))
                _modsFiltersToolbar.Controls.Add(_modsSearchLabel);
            if (!_modsFiltersToolbar.Controls.Contains(_modsSearchBorderPanel))
                _modsFiltersToolbar.Controls.Add(_modsSearchBorderPanel);
        }

        private void ModsSearchTextBox_TextChanged(object sender, EventArgs e)
        {
            Port_SearchTextChanged(_modsSearchTextBox?.Text);
        }

        private void ModsSearchTextBox_MouseEnter(object sender, EventArgs e)
        {
            _modsSearchHover = true;
            UpdateModsSearchBorderColor();
        }

        private void ModsSearchTextBox_MouseLeave(object sender, EventArgs e)
        {
            _modsSearchHover = false;
            UpdateModsSearchBorderColor();
        }

        private void ModsSearchTextBox_Enter(object sender, EventArgs e)
        {
            _modsSearchFocused = true;
            UpdateModsSearchBorderColor();
        }

        private void ModsSearchTextBox_Leave(object sender, EventArgs e)
        {
            _modsSearchFocused = false;
            UpdateModsSearchBorderColor();
        }

        private void UpdateModsSearchBorderColor()
        {
            if (_modsSearchBorderPanel == null)
                return;

            if (_modsSearchFocused)
            {
                _modsSearchBorderPanel.BackColor = Color.FromArgb(120, 120, 120);
                return;
            }

            if (_modsSearchHover)
            {
                _modsSearchBorderPanel.BackColor = Color.FromArgb(105, 105, 105);
                return;
            }

            _modsSearchBorderPanel.BackColor = Color.FromArgb(90, 90, 90);
        }

        private void EnsureModsHeader()
        {
            if (groupBoxMods == null || _modsSectionHost == null)
                return;

            if (_modsHeaderPanel != null)
                return;

            // Replace the GroupBox caption with an internal header row so we can right-align counters.
            groupBoxMods.Text = string.Empty;

            _modsHeaderPanel = new Panel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Padding = new Padding(6, 4, 8, 4),
                Margin = new Padding(0)
            };

            _modsHeaderTable = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Margin = new Padding(0),
                Padding = new Padding(0),
                ColumnCount = 2,
                RowCount = 1
            };
            _modsHeaderTable.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            _modsHeaderTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            _modsHeaderTable.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var leftFlow = new FlowLayoutPanel
            {
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false,
                Margin = new Padding(0),
                Padding = new Padding(0)
            };

            _modsHeaderTitle = new Label
            {
                AutoSize = true,
                Text = "Mods",
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(0, 0, 8, 0)
            };

            leftFlow.Controls.Add(_modsHeaderTitle);

            // Add Load Order Path controls inline after the title
            EnsureTopPathRowInHeader(leftFlow);

            _modsCountersFlow = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                FlowDirection = FlowDirection.RightToLeft,
                WrapContents = true,
                Margin = new Padding(0),
                Padding = new Padding(0)
            };

            _modsHeaderTable.Controls.Add(leftFlow, 0, 0);
            _modsHeaderTable.Controls.Add(_modsCountersFlow, 1, 0);

            _modsHeaderPanel.Controls.Add(_modsHeaderTable);
            _modsSectionHost.Controls.Add(_modsHeaderPanel);
            _modsSectionHost.Controls.SetChildIndex(_modsHeaderPanel, 0);

            // Keep labelStats as the source of truth for the backend/update flow, but hide it.
            if (labelStats != null)
            {
                labelStats.Visible = false;
                labelStats.TextChanged -= LabelStats_TextChanged;
                labelStats.TextChanged += LabelStats_TextChanged;
            }

            BuildModsCounterControls();
            UpdateModsCountersFromLabelStats();
        }

        private void EnsureTopPathRowInHeader(FlowLayoutPanel parent)
        {
            if (parent == null)
                return;

            if (_topPathLabel != null)
                return;

            _topPathLabel = new Label
            {
                AutoSize = true,
                Text = "Load Order Path:",
                ForeColor = Color.LightGray,
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(0, 0, 8, 0)
            };

            _topPathTextBox = new TextBox
            {
                ReadOnly = true,
                BackColor = Color.FromArgb(35, 35, 35),
                ForeColor = Color.LightGray,
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                BorderStyle = BorderStyle.FixedSingle,
                Width = 420,
                Margin = new Padding(0, 0, 8, 0)
            };

            _topPathBrowseButton = new Button
            {
                Text = "Browse",
                AutoSize = false,
                Width = 80,
                Height = 28,
                UseVisualStyleBackColor = false,
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(70, 130, 180),
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                Margin = new Padding(0)
            };
            _topPathBrowseButton.FlatAppearance.BorderSize = 0;
            _topPathBrowseButton.Click -= TopPathBrowseButton_Click;
            _topPathBrowseButton.Click += TopPathBrowseButton_Click;

            parent.Controls.Add(_topPathLabel);
            parent.Controls.Add(_topPathTextBox);
            parent.Controls.Add(_topPathBrowseButton);
        }

        private void BuildModsCounterControls()
        {
            if (_modsCountersFlow == null)
                return;

            _modsCountersFlow.Controls.Clear();

            _conflictsCountValue = AddCounter("Conflicts:");
            _enabledCountValue = AddCounter("Enabled:");
            _modsCountValue = AddCounter("Mods:");
        }

        private Label AddCounter(string labelText)
        {
            if (_modsCountersFlow == null)
                return null;

            var group = new FlowLayoutPanel
            {
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false,
                Margin = new Padding(12, 0, 0, 0),
                Padding = new Padding(0)
            };

            var label = new Label
            {
                AutoSize = true,
                Text = labelText,
                ForeColor = Color.FromArgb(160, 160, 160),
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(0, 0, 4, 0)
            };

            var value = new Label
            {
                AutoSize = true,
                Text = "0",
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(0)
            };

            group.Controls.Add(label);
            group.Controls.Add(value);

            _modsCountersFlow.Controls.Add(group);
            return value;
        }

        private void LabelStats_TextChanged(object sender, EventArgs e)
        {
            UpdateModsCountersFromLabelStats();
        }

        private void UpdateModsCountersFromLabelStats()
        {
            if (labelStats == null)
                return;

            string text = labelStats.Text ?? string.Empty;

            SetCounterValueFromStats(text, "Mods:", _modsCountValue);
            SetCounterValueFromStats(text, "Enabled:", _enabledCountValue);
            SetCounterValueFromStats(text, "Conflicts:", _conflictsCountValue);
        }

        private void SetCounterValueFromStats(string statsText, string key, Label target)
        {
            if (target == null)
                return;

            int idx = statsText.IndexOf(key, StringComparison.OrdinalIgnoreCase);
            if (idx < 0)
                return;

            idx += key.Length;
            while (idx < statsText.Length && statsText[idx] == ' ')
                idx++;

            int end = statsText.IndexOf('|', idx);
            if (end < 0)
                end = statsText.Length;

            string value = statsText.Substring(idx, end - idx).Trim();
            if (value.Length == 0)
                return;

            target.Text = value;
        }

        private void EnsureCategoryDropdownChrome()
        {
            if (_modsFiltersToolbar == null || comboBoxCategory == null)
                return;

            if (_categoryBorderPanel == null)
            {
                _categoryBorderPanel = new Panel
                {
                    Width = 180,
                    Height = 28,
                    Padding = new Padding(1),
                    Margin = new Padding(0, 4, 10, 4),
                    BackColor = Color.FromArgb(90, 90, 90)
                };

                // Place the border panel into the toolbar right after the Category label if possible.
                int insertIndex = _modsFiltersToolbar.Controls.IndexOf(labelCategory);
                if (insertIndex < 0)
                    insertIndex = _modsFiltersToolbar.Controls.Count;
                else
                    insertIndex++;

                _modsFiltersToolbar.Controls.Add(_categoryBorderPanel);
                _modsFiltersToolbar.Controls.SetChildIndex(_categoryBorderPanel, insertIndex);

                _categoryBorderPanel.Controls.Add(comboBoxCategory);
                comboBoxCategory.Dock = DockStyle.Fill;
                comboBoxCategory.Margin = new Padding(0);

                comboBoxCategory.FlatStyle = FlatStyle.Flat;
                comboBoxCategory.BackColor = Color.FromArgb(35, 35, 35);
                comboBoxCategory.ForeColor = Color.LightGray;

                // Owner draw gives us clean internal padding and vertical centering.
                comboBoxCategory.DrawMode = DrawMode.OwnerDrawFixed;
                comboBoxCategory.ItemHeight = 20;
                comboBoxCategory.DrawItem -= ComboBoxCategory_DrawItem;
                comboBoxCategory.DrawItem += ComboBoxCategory_DrawItem;

                comboBoxCategory.MouseEnter -= ComboBoxCategory_MouseEnter;
                comboBoxCategory.MouseEnter += ComboBoxCategory_MouseEnter;
                comboBoxCategory.MouseLeave -= ComboBoxCategory_MouseLeave;
                comboBoxCategory.MouseLeave += ComboBoxCategory_MouseLeave;
                comboBoxCategory.Enter -= ComboBoxCategory_Enter;
                comboBoxCategory.Enter += ComboBoxCategory_Enter;
                comboBoxCategory.Leave -= ComboBoxCategory_Leave;
                comboBoxCategory.Leave += ComboBoxCategory_Leave;

                UpdateCategoryBorderColor();
            }
            else
            {
                // If the combo was reparented elsewhere, bring it back under the border panel.
                if (comboBoxCategory.Parent != _categoryBorderPanel)
                {
                    if (comboBoxCategory.Parent != null)
                        comboBoxCategory.Parent.Controls.Remove(comboBoxCategory);
                    _categoryBorderPanel.Controls.Add(comboBoxCategory);
                    comboBoxCategory.Dock = DockStyle.Fill;
                    comboBoxCategory.Margin = new Padding(0);
                }
            }
        }

        private void ComboBoxCategory_DrawItem(object sender, DrawItemEventArgs e)
        {
            if (comboBoxCategory == null)
                return;

            e.DrawBackground();

            if (e.Index < 0)
                return;

            var item = comboBoxCategory.Items[e.Index] as string;
            if (item == null)
                return;

            var bounds = e.Bounds;
            bounds.X += 8;
            bounds.Width -= 12;

            var textColor = comboBoxCategory.ForeColor;
            TextRenderer.DrawText(
                e.Graphics,
                item,
                comboBoxCategory.Font,
                bounds,
                textColor,
                TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis);

            e.DrawFocusRectangle();
        }

        private void ComboBoxCategory_MouseEnter(object sender, EventArgs e)
        {
            _categoryHover = true;
            UpdateCategoryBorderColor();
        }

        private void ComboBoxCategory_MouseLeave(object sender, EventArgs e)
        {
            _categoryHover = false;
            UpdateCategoryBorderColor();
        }

        private void ComboBoxCategory_Enter(object sender, EventArgs e)
        {
            _categoryFocused = true;
            UpdateCategoryBorderColor();
        }

        private void ComboBoxCategory_Leave(object sender, EventArgs e)
        {
            _categoryFocused = false;
            UpdateCategoryBorderColor();
        }

        private void UpdateCategoryBorderColor()
        {
            if (_categoryBorderPanel == null)
                return;

            if (_categoryFocused)
            {
                _categoryBorderPanel.BackColor = Color.FromArgb(120, 120, 120);
                return;
            }

            if (_categoryHover)
            {
                _categoryBorderPanel.BackColor = Color.FromArgb(105, 105, 105);
                return;
            }

            _categoryBorderPanel.BackColor = Color.FromArgb(90, 90, 90);
        }

        private void AddToModsToolbar(Control c)
        {
            if (_modsFiltersToolbar == null || c == null)
                return;

            if (!_modsFiltersToolbar.Controls.Contains(c))
                _modsFiltersToolbar.Controls.Add(c);
        }

        private void EnsureTopActionButtonTable()
        {
            if (tableTop == null)
                return;

            if (flowTopActions != null && tableTop.Controls.Contains(flowTopActions))
            {
                tableTop.Controls.Remove(flowTopActions);
                flowTopActions.Visible = false;
            }

            if (_topActionsTable == null)
            {
                _topActionsTable = new TableLayoutPanel
                {
                    Dock = DockStyle.Top,
                    AutoSize = false,
                    GrowStyle = TableLayoutPanelGrowStyle.AddRows,
                    Padding = new Padding(6),
                    Margin = new Padding(0)
                };

                tableTop.Controls.Add(_topActionsTable, 0, 0);
                tableTop.Resize -= TableTop_Resize;
                tableTop.Resize += TableTop_Resize;
            }

            var buttons = GetTopActionButtons();

            foreach (var b in buttons)
            {
                if (b == null)
                    continue;

                b.Dock = DockStyle.Fill;
                b.AutoSize = false;
                b.MinimumSize = new Size(120, 36);
                b.TextAlign = ContentAlignment.MiddleCenter;
                b.Padding = new Padding(6, 3, 6, 3);
                b.Margin = new Padding(6);
                b.UseCompatibleTextRendering = true;
                b.AutoEllipsis = true;
                b.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
            }

            ReflowTopActionButtonTable(buttons);
        }

        private void TableTop_Resize(object sender, EventArgs e)
        {
            if (_topActionsTable == null)
                return;

            var buttons = GetTopActionButtons();

            ReflowTopActionButtonTable(buttons);
        }

        private void ReflowTopActionButtonTable(Button[] buttons)
        {
            if (_topActionsTable == null || buttons == null)
                return;

            int buttonCount = 0;
            foreach (var b in buttons)
                if (b != null)
                    buttonCount++;

            if (buttonCount == 0)
                return;

            int available = _topActionsTable.Parent?.ClientSize.Width ?? _topActionsTable.ClientSize.Width;
            if (available <= 0)
                available = this.ClientSize.Width;

            int columns = Math.Max(1, available / 180);
            if (columns == _topActionsColumns && _topActionsTable.Controls.Count == buttonCount)
                return;

            _topActionsColumns = columns;

            _topActionsTable.SuspendLayout();
            try
            {
                _topActionsTable.Controls.Clear();
                _topActionsTable.ColumnStyles.Clear();
                _topActionsTable.RowStyles.Clear();

                _topActionsTable.ColumnCount = columns;
                float pct = 100F / columns;
                for (int c = 0; c < columns; c++)
                    _topActionsTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, pct));

                int rows = (int)Math.Ceiling(buttonCount / (double)columns);
                _topActionsTable.RowCount = rows;
                for (int r = 0; r < rows; r++)
                    _topActionsTable.RowStyles.Add(new RowStyle(SizeType.Absolute, 46F));

                // Keep the host row sized to the number of wrapped rows to prevent clipping.
                int desiredHeight = (rows * 46) + _topActionsTable.Padding.Vertical;
                _topActionsTable.Height = desiredHeight;
                if (tableTop != null && tableTop.RowStyles.Count > 0)
                {
                    tableTop.RowStyles[0].SizeType = SizeType.Absolute;
                    tableTop.RowStyles[0].Height = desiredHeight;
                }

                int index = 0;
                foreach (var b in buttons)
                {
                    if (b == null)
                        continue;

                    int r = index / columns;
                    int c = index % columns;
                    _topActionsTable.Controls.Add(b, c, r);
                    index++;
                }
            }
            finally
            {
                _topActionsTable.ResumeLayout();
            }
        }

        private void EnsureFiltersRow()
        {
            if (flowControlFilters == null)
                return;

            flowControlFilters.AutoScroll = false;
            flowControlFilters.WrapContents = true;
            flowControlFilters.FlowDirection = FlowDirection.LeftToRight;
            flowControlFilters.Dock = DockStyle.Top;
            flowControlFilters.Padding = new Padding(6);
            flowControlFilters.HorizontalScroll.Enabled = false;
            flowControlFilters.HorizontalScroll.Visible = false;

            var filterControls = new Control[]
            {
                buttonFilterCritical,
                buttonFilterHigh,
                buttonFilterLow,
                buttonFilterRedundant,
                buttonFilterDisabled,
                buttonFilterOK
            };

            for (int i = filterControls.Length - 1; i >= 0; i--)
            {
                var c = filterControls[i];
                if (c == null)
                    continue;

                MoveControlTo(c, flowControlFilters);
                flowControlFilters.Controls.SetChildIndex(c, 0);
            }
        }

        private void NormalizeLayout()
        {
            if (tableMain != null && tableMain.RowStyles.Count >= 5)
            {
                tableMain.RowStyles[0].SizeType = SizeType.Absolute;
                tableMain.RowStyles[0].Height = 240F;

                tableMain.RowStyles[1].SizeType = SizeType.Percent;
                tableMain.RowStyles[1].Height = 100F;

                tableMain.RowStyles[2].SizeType = SizeType.Absolute;
                tableMain.RowStyles[2].Height = 8F;

                tableMain.RowStyles[3].SizeType = SizeType.Absolute;
                tableMain.RowStyles[3].Height = 240F;

                tableMain.RowStyles[4].SizeType = SizeType.Absolute;
                tableMain.RowStyles[4].Height = 34F;
            }

            if (panelSpacer != null)
            {
                panelSpacer.Height = 8;
                panelSpacer.Margin = new Padding(0);
                panelSpacer.Dock = DockStyle.Fill;
            }

            if (groupBoxMods != null)
            {
                groupBoxMods.Dock = DockStyle.Fill;
                groupBoxMods.Visible = true;
                groupBoxMods.Enabled = true;
                groupBoxMods.MinimumSize = new Size(0, 250);
            }

            if (dataGridViewMods != null)
            {
                dataGridViewMods.Dock = DockStyle.Fill;
                dataGridViewMods.Visible = true;
                dataGridViewMods.Enabled = true;
            }

            if (panelTop != null)
            {
                panelTop.Dock = DockStyle.Fill;
                panelTop.Margin = new Padding(6);
                panelTop.Padding = new Padding(8);
            }

            if (flowTopActions != null)
            {
                flowTopActions.AutoScroll = false;
                flowTopActions.WrapContents = true;
                flowTopActions.AutoSize = true;
                flowTopActions.AutoSizeMode = AutoSizeMode.GrowAndShrink;
                flowTopActions.Dock = DockStyle.Top;
                flowTopActions.HorizontalScroll.Enabled = false;
                flowTopActions.HorizontalScroll.Visible = false;
                flowTopActions.FlowDirection = FlowDirection.LeftToRight;
            }

            if (panelHeatmapScroll != null)
            {
                panelHeatmapScroll.Dock = DockStyle.Fill;
                panelHeatmapScroll.AutoScroll = true;
                panelHeatmapScroll.BringToFront();
                panelHeatmapScroll.Resize -= PanelHeatmapScroll_Resize;
                panelHeatmapScroll.Resize += PanelHeatmapScroll_Resize;
            }
        }

        private void PopulateCategoryDropdown()
        {
            if (comboBoxCategory == null)
                return;

            var items = new object[]
            {
                "All",
                "Overhauls",
                "XML Edits",
                "Gameplay",
                "Crafting",
                "Weapons",
                "Items & Loot",
                "Zombies / Creatures",
                "Quests",
                "Prefabs / POIs",
                "UI",
                "Libraries / Dependencies",
                "Visual / Audio",
                "Performance"
            };

            comboBoxCategory.BeginUpdate();
            try
            {
                comboBoxCategory.Items.Clear();
                comboBoxCategory.Items.AddRange(items);
                if (comboBoxCategory.Items.Count > 0)
                    comboBoxCategory.SelectedIndex = 0;
            }
            finally
            {
                comboBoxCategory.EndUpdate();
            }

            EnsureCategoryDropdownSorted();

            comboBoxCategory.DropDown -= ComboBoxCategory_DropDown;
            comboBoxCategory.DropDown += ComboBoxCategory_DropDown;
        }

        private void EnsureCategoryDropdownSorted()
        {
            if (comboBoxCategory == null)
                return;

            var current = comboBoxCategory.SelectedItem as string;

            var ordered = new List<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            bool hasAll = false;
            var rest = new List<(string value, int index)>();

            for (int i = 0; i < comboBoxCategory.Items.Count; i++)
            {
                var s = comboBoxCategory.Items[i] as string;
                if (string.IsNullOrWhiteSpace(s))
                    continue;

                if (!seen.Add(s))
                    continue;

                if (string.Equals(s, "All", StringComparison.OrdinalIgnoreCase))
                {
                    hasAll = true;
                    continue;
                }

                rest.Add((s, i));
            }

            rest.Sort((a, b) =>
            {
                int cmp = StringComparer.OrdinalIgnoreCase.Compare(a.value, b.value);
                if (cmp != 0)
                    return cmp;
                return a.index.CompareTo(b.index);
            });

            if (hasAll)
                ordered.Add("All");

            foreach (var item in rest)
                ordered.Add(item.value);

            comboBoxCategory.BeginUpdate();
            try
            {
                comboBoxCategory.Items.Clear();
                comboBoxCategory.Items.AddRange(ordered.ToArray());
            }
            finally
            {
                comboBoxCategory.EndUpdate();
            }

            if (current != null)
            {
                int idx = comboBoxCategory.Items.IndexOf(current);
                if (idx >= 0)
                    comboBoxCategory.SelectedIndex = idx;
                else if (comboBoxCategory.Items.Count > 0)
                    comboBoxCategory.SelectedIndex = 0;
            }
            else if (comboBoxCategory.Items.Count > 0)
            {
                comboBoxCategory.SelectedIndex = 0;
            }
        }

        private void BuildLegend()
        {
            if (flowLegend == null)
                return;

            flowLegend.SuspendLayout();
            try
            {
                flowLegend.Controls.Clear();
                flowLegend.Padding = new Padding(8);

                AddLegendItem("Critical", HeatmapCritical);
                AddLegendItem("High", HeatmapHigh);
                AddLegendItem("Low", HeatmapLow);
                AddLegendItem("Redundant", HeatmapRedundant);
                AddLegendItem("Disabled", HeatmapDisabled);
                AddLegendItem("OK", HeatmapOk);
            }
            finally
            {
                flowLegend.ResumeLayout();
            }
        }

        private void AddLegendItem(string text, Color color)
        {
            var container = new FlowLayoutPanel
            {
                AutoSize = true,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false,
                Margin = new Padding(6, 4, 12, 4),
                Padding = new Padding(0)
            };

            var swatch = new Panel
            {
                Width = 12,
                Height = 12,
                BackColor = color,
                BorderStyle = BorderStyle.FixedSingle,
                Margin = new Padding(0, 3, 6, 0)
            };

            var label = new Label
            {
                AutoSize = true,
                Text = text,
                ForeColor = Color.LightGray,
                Margin = new Padding(0, 1, 0, 0)
            };

            container.Controls.Add(swatch);
            container.Controls.Add(label);
            flowLegend.Controls.Add(container);
        }

        private void RenderHeatmapEmptyState()
        {
            if (panelHeatmapScroll == null || flowHeatmap == null)
                return;

            // The designer wires flowHeatmap.ControlAdded to style cells; for our composite layout
            // we manage child styling ourselves to preserve colors.
            flowHeatmap.ControlAdded -= flowHeatmap_ControlAdded;

            _heatmapSegmentFractions.Clear();
            _heatmapSegmentTargets.Clear();
            _heatmapBarContainers.Clear();
            _heatmapOriginalColors.Clear();
            _heatmapRowGroups.Clear();

            flowHeatmap.SuspendLayout();
            try
            {
                flowHeatmap.Controls.Clear();
                flowHeatmap.AutoSize = false;
                flowHeatmap.Dock = DockStyle.Fill;
                flowHeatmap.WrapContents = false;
                flowHeatmap.FlowDirection = FlowDirection.TopDown;

                _heatmapTable = new TableLayoutPanel
                {
                    ColumnCount = 2,
                    AutoSize = true,
                    Dock = DockStyle.Top,
                    Padding = new Padding(10),
                    BackColor = Color.FromArgb(25, 25, 25)
                };

                _heatmapTable.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 160F));
                _heatmapTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));

                // Header row
                _heatmapTable.RowStyles.Add(new RowStyle(SizeType.Absolute, 28F));
                var headerLeft = new Label
                {
                    Text = "Category",
                    AutoSize = false,
                    Height = 22,
                    Dock = DockStyle.Fill,
                    ForeColor = Color.FromArgb(210, 210, 210),
                    BackColor = Color.FromArgb(35, 35, 35),
                    Font = new Font("Microsoft Sans Serif", 9F, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Padding = new Padding(6, 0, 0, 0),
                    Margin = new Padding(0)
                };

                var headerRight = new Label
                {
                    Text = "Risk",
                    AutoSize = false,
                    Height = 22,
                    Dock = DockStyle.Fill,
                    ForeColor = Color.FromArgb(210, 210, 210),
                    BackColor = Color.FromArgb(35, 35, 35),
                    Font = new Font("Microsoft Sans Serif", 9F, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Padding = new Padding(6, 0, 0, 0),
                    Margin = new Padding(0)
                };

                _heatmapTable.Controls.Add(headerLeft, 0, 0);
                _heatmapTable.Controls.Add(headerRight, 1, 0);

                flowHeatmap.Controls.Add(_heatmapTable);
            }
            finally
            {
                flowHeatmap.ResumeLayout();
            }

            UpdateHeatmapBarWidths();
        }

        private void RenderHeatmap(List<CategorySnapshot> categories)
        {
            if (categories == null || categories.Count == 0)
            {
                RenderHeatmapEmptyState();
                return;
            }

            if (panelHeatmapScroll == null || flowHeatmap == null)
                return;

            flowHeatmap.ControlAdded -= flowHeatmap_ControlAdded;

            StopHeatmapAnimation();

            _heatmapSegmentFractions.Clear();
            _heatmapSegmentTargets.Clear();
            _heatmapBarContainers.Clear();
            _heatmapOriginalColors.Clear();
            _heatmapRowGroups.Clear();

            flowHeatmap.SuspendLayout();
            try
            {
                flowHeatmap.Controls.Clear();
                flowHeatmap.AutoSize = false;
                flowHeatmap.Dock = DockStyle.Fill;
                flowHeatmap.WrapContents = false;
                flowHeatmap.FlowDirection = FlowDirection.TopDown;

                _heatmapTable = new TableLayoutPanel
                {
                    ColumnCount = 2,
                    AutoSize = true,
                    Dock = DockStyle.Top,
                    Padding = new Padding(10),
                    BackColor = Color.FromArgb(25, 25, 25)
                };

                _heatmapTable.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 160F));
                _heatmapTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));

                _heatmapTable.RowStyles.Add(new RowStyle(SizeType.Absolute, 28F));
                var headerLeft = new Label
                {
                    Text = "Category",
                    AutoSize = false,
                    Height = 22,
                    Dock = DockStyle.Fill,
                    ForeColor = Color.FromArgb(210, 210, 210),
                    BackColor = Color.FromArgb(35, 35, 35),
                    Font = new Font("Microsoft Sans Serif", 9F, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Padding = new Padding(6, 0, 0, 0),
                    Margin = new Padding(0)
                };

                var headerRight = new Label
                {
                    Text = "Risk",
                    AutoSize = false,
                    Height = 22,
                    Dock = DockStyle.Fill,
                    ForeColor = Color.FromArgb(210, 210, 210),
                    BackColor = Color.FromArgb(35, 35, 35),
                    Font = new Font("Microsoft Sans Serif", 9F, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft,
                    Padding = new Padding(6, 0, 0, 0),
                    Margin = new Padding(0)
                };

                _heatmapTable.Controls.Add(headerLeft, 0, 0);
                _heatmapTable.Controls.Add(headerRight, 1, 0);

                int rowIndex = 1;
                for (int i = 0; i < categories.Count; i++)
                {
                    var cat = categories[i];
                    if (cat == null)
                        continue;
                    if (cat.TotalMods <= 0)
                        continue;
                    if (string.IsNullOrWhiteSpace(cat.Category))
                        continue;
                    if (cat.Percentages == null || cat.Percentages.Count == 0)
                        continue;

                    _heatmapTable.RowStyles.Add(new RowStyle(SizeType.Absolute, 30F));

                    var stripe = ((rowIndex - 1) % 2 == 0)
                        ? Color.FromArgb(28, 28, 28)
                        : Color.FromArgb(24, 24, 24);

                    var rowGroup = new List<Control>();

                    var label = new Label
                    {
                        Text = cat.Category,
                        AutoSize = false,
                        Width = 160,
                        Height = 24,
                        ForeColor = Color.LightGray,
                        TextAlign = ContentAlignment.MiddleLeft,
                        Margin = new Padding(0),
                        Padding = new Padding(6, 0, 0, 0),
                        BackColor = stripe
                    };

                    var barContainer = new Panel
                    {
                        Height = 18,
                        Dock = DockStyle.Fill,
                        BackColor = stripe,
                        Margin = new Padding(0),
                        Padding = new Padding(6, 6, 6, 6),
                        Tag = cat.Category
                    };

                    var barInner = new Panel
                    {
                        Height = 18,
                        Dock = DockStyle.Fill,
                        BackColor = Color.FromArgb(30, 30, 30),
                        Margin = new Padding(0),
                        Tag = cat.Category
                    };

                    barContainer.Controls.Add(barInner);

                    AddHeatmapSegmentFromPercent(barInner, cat, "OK", HeatmapOk);
                    AddHeatmapSegmentFromPercent(barInner, cat, "Disabled", HeatmapDisabled);
                    AddHeatmapSegmentFromPercent(barInner, cat, "Redundant", HeatmapRedundant);
                    AddHeatmapSegmentFromPercent(barInner, cat, "Low", HeatmapLow);
                    AddHeatmapSegmentFromPercent(barInner, cat, "High", HeatmapHigh);
                    AddHeatmapSegmentFromPercent(barInner, cat, "Critical", HeatmapCritical);

                    _heatmapBarContainers.Add(barInner);

                    var sepLeft = new Panel
                    {
                        Dock = DockStyle.Bottom,
                        Height = 1,
                        BackColor = Color.FromArgb(45, 45, 45)
                    };
                    var sepRight = new Panel
                    {
                        Dock = DockStyle.Bottom,
                        Height = 1,
                        BackColor = Color.FromArgb(45, 45, 45)
                    };

                    label.Controls.Add(sepLeft);
                    barContainer.Controls.Add(sepRight);

                    rowGroup.Add(label);
                    rowGroup.Add(barContainer);
                    foreach (Control seg in barInner.Controls)
                        rowGroup.Add(seg);

                    foreach (var c in rowGroup)
                    {
                        RememberHeatmapOriginalColors(c);
                        WireHeatmapRowHover(c, rowGroup);
                    }

                    _heatmapTable.Controls.Add(label, 0, rowIndex);
                    _heatmapTable.Controls.Add(barContainer, 1, rowIndex);
                    rowIndex++;
                }

                flowHeatmap.Controls.Add(_heatmapTable);
            }
            finally
            {
                flowHeatmap.ResumeLayout();
            }

            StartHeatmapAnimation();
        }

        private void AddHeatmapSegmentFromPercent(Panel barContainer, CategorySnapshot cat, string severityName, Color color)
        {
            if (barContainer == null || cat == null || cat.Percentages == null)
                return;

            double pct = 0.0;
            foreach (var kv in cat.Percentages)
            {
                if (string.Equals(kv.Key, severityName, StringComparison.OrdinalIgnoreCase))
                {
                    pct = kv.Value;
                    break;
                }
            }

            if (pct <= 0.0)
                return;

            float target = (float)(pct / 100.0);
            var segment = new Panel
            {
                Dock = DockStyle.Left,
                Height = 18,
                BackColor = color,
                Margin = new Padding(0),
                Cursor = Cursors.Hand,
                Tag = barContainer.Tag
            };

            toolTipHeatmap?.SetToolTip(segment, severityName);
            segment.Click += HeatmapCell_Click;

            _heatmapSegmentFractions[segment] = 0f;
            _heatmapSegmentTargets[segment] = target;
            barContainer.Controls.Add(segment);
        }

        private void StartHeatmapAnimation()
        {
            if (_heatmapSegmentTargets.Count == 0)
            {
                UpdateHeatmapBarWidths();
                return;
            }

            if (_heatmapAnimTimer == null)
            {
                _heatmapAnimTimer = new System.Windows.Forms.Timer();
                _heatmapAnimTimer.Interval = 15;
                _heatmapAnimTimer.Tick += HeatmapAnimTimer_Tick;
            }

            _heatmapAnimStartTick = Environment.TickCount;
            _heatmapAnimTimer.Start();
        }

        private void StopHeatmapAnimation()
        {
            if (_heatmapAnimTimer != null)
                _heatmapAnimTimer.Stop();
        }

        private void HeatmapAnimTimer_Tick(object sender, EventArgs e)
        {
            const int durationMs = 220;
            int elapsed = Environment.TickCount - _heatmapAnimStartTick;
            if (elapsed < 0)
                elapsed = 0;

            float t = Math.Min(1f, elapsed / (float)durationMs);
            // Smoothstep easing for nicer motion.
            t = t * t * (3f - 2f * t);

            foreach (var kv in _heatmapSegmentTargets)
            {
                var seg = kv.Key;
                if (seg == null)
                    continue;

                _heatmapSegmentFractions[seg] = kv.Value * t;
            }

            UpdateHeatmapBarWidths();

            if (t >= 1f)
            {
                foreach (var kv in _heatmapSegmentTargets)
                {
                    if (kv.Key == null)
                        continue;
                    _heatmapSegmentFractions[kv.Key] = kv.Value;
                }

                StopHeatmapAnimation();
                UpdateHeatmapBarWidths();
            }
        }

        private void RememberHeatmapOriginalColors(Control c)
        {
            if (c == null)
                return;

            if (_heatmapOriginalColors.ContainsKey(c))
                return;

            _heatmapOriginalColors[c] = (c.BackColor, c.ForeColor);
        }

        private void WireHeatmapRowHover(Control c, List<Control> rowGroup)
        {
            if (c == null || rowGroup == null)
                return;

            if (!_heatmapRowGroups.ContainsKey(c))
                _heatmapRowGroups[c] = rowGroup;

            c.MouseEnter -= HeatmapRow_MouseEnter;
            c.MouseLeave -= HeatmapRow_MouseLeave;
            c.MouseEnter += HeatmapRow_MouseEnter;
            c.MouseLeave += HeatmapRow_MouseLeave;
        }

        private void HeatmapRow_MouseEnter(object sender, EventArgs e)
        {
            var src = sender as Control;
            if (src == null)
                return;

            if (!_heatmapRowGroups.TryGetValue(src, out var rowGroup))
                return;

            var highlight = Color.FromArgb(55, 55, 55);
            foreach (var c in rowGroup)
            {
                if (c is Panel p)
                {
                    // Don't override actual severity segments
                    if (_heatmapSegmentFractions.ContainsKey(p))
                        continue;
                }

                c.BackColor = highlight;
            }
        }

        private void HeatmapRow_MouseLeave(object sender, EventArgs e)
        {
            var src = sender as Control;
            if (src == null)
                return;

            if (!_heatmapRowGroups.TryGetValue(src, out var rowGroup))
                return;

            foreach (var c in rowGroup)
            {
                if (_heatmapOriginalColors.TryGetValue(c, out var colors))
                {
                    c.BackColor = colors.normalBack;
                    c.ForeColor = colors.normalFore;
                }
            }
        }

        private void AddHeatmapSegment(Panel barContainer, float fraction, Color color, string severityName)
        {
            if (barContainer == null)
                return;

            // Skip near-zero segments to keep the UI readable.
            if (fraction < 0.01f)
                return;

            var segment = new Panel
            {
                Dock = DockStyle.Left,
                Height = 18,
                BackColor = color,
                Margin = new Padding(0),
                Cursor = Cursors.Hand,
                Tag = barContainer.Tag
            };

            toolTipHeatmap?.SetToolTip(segment, severityName);
            segment.Click += HeatmapCell_Click;

            _heatmapSegmentFractions[segment] = fraction;
            barContainer.Controls.Add(segment);
        }

        private void PanelHeatmapScroll_Resize(object sender, EventArgs e)
        {
            UpdateHeatmapBarWidths();
        }

        private void UpdateHeatmapBarWidths()
        {
            if (panelHeatmapScroll != null)
            {
                // Force a vertical scrollbar to be available (even if content barely fits)
                // by ensuring the scrollable height is at least slightly larger than the viewport.
                var minHeight = panelHeatmapScroll.ClientSize.Height + 1;
                if (_heatmapTable != null)
                    minHeight = Math.Max(minHeight, _heatmapTable.PreferredSize.Height + 20);

                panelHeatmapScroll.AutoScrollMinSize = new Size(0, minHeight);
            }

            foreach (var barContainer in _heatmapBarContainers)
            {
                if (barContainer == null)
                    continue;

                int available = Math.Max(0, barContainer.ClientSize.Width);
                if (available <= 0)
                    continue;

                var segments = new List<Panel>();
                var fractions = new List<float>();

                foreach (Control c in barContainer.Controls)
                {
                    if (c is Panel p && _heatmapSegmentFractions.TryGetValue(p, out float frac))
                    {
                        segments.Add(p);
                        fractions.Add(frac);
                    }
                }

                if (segments.Count == 0)
                    continue;

                var widths = new int[segments.Count];
                int sum = 0;
                for (int i = 0; i < segments.Count; i++)
                {
                    int w = (int)Math.Round(available * fractions[i]);

                    widths[i] = w;
                    sum += w;
                }

                // Distribute remainder (positive or negative) to last segment so total == available.
                int remainder2 = available - sum;
                widths[widths.Length - 1] = Math.Max(0, widths[widths.Length - 1] + remainder2);

                for (int i = 0; i < segments.Count; i++)
                {
                    segments[i].Width = widths[i];
                }
            }
        }

        private void flowHeatmap_Paint(object sender, PaintEventArgs e)
        {

        }

        private void panelTop_Paint(object sender, PaintEventArgs e)
        {

        }

        private void dataGridViewMods_CellContentClick(object sender, DataGridViewCellEventArgs e)
        {

        }
    }
}
