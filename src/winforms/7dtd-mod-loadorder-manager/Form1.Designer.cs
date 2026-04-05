namespace ModManagerPrototype
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            this.tableMain = new System.Windows.Forms.TableLayoutPanel();
            this.panelTop = new System.Windows.Forms.Panel();
            this.tableTop = new System.Windows.Forms.TableLayoutPanel();
            this.flowTopActions = new System.Windows.Forms.FlowLayoutPanel();
            this.buttonScanMods = new System.Windows.Forms.Button();
            this.buttonGenerateApplyLoadOrder = new System.Windows.Forms.Button();
            this.buttonExportLoadOrder = new System.Windows.Forms.Button();
            this.buttonRenameFolder = new System.Windows.Forms.Button();
            this.buttonExplainIssues = new System.Windows.Forms.Button();
            this.buttonResolveConflicts = new System.Windows.Forms.Button();
            this.buttonFindDuplicates = new System.Windows.Forms.Button();
            this.buttonApplyUpdateFixes = new System.Windows.Forms.Button();
            this.buttonExplainSelected = new System.Windows.Forms.Button();
            this.buttonDiagnoseVisibility = new System.Windows.Forms.Button();
            this.buttonFilterOK = new System.Windows.Forms.Button();
            this.buttonFilterDisabled = new System.Windows.Forms.Button();
            this.buttonFilterRedundant = new System.Windows.Forms.Button();
            this.buttonFilterLow = new System.Windows.Forms.Button();
            this.buttonFilterHigh = new System.Windows.Forms.Button();
            this.buttonFilterCritical = new System.Windows.Forms.Button();
            this.labelStats = new System.Windows.Forms.Label();
            this.flowControlFilters = new System.Windows.Forms.FlowLayoutPanel();
            this.labelCategory = new System.Windows.Forms.Label();
            this.comboBoxCategory = new System.Windows.Forms.ComboBox();
            this.labelSeverity = new System.Windows.Forms.Label();
            this.trackBarSeverity = new System.Windows.Forms.TrackBar();
            this.checkBoxConflictsOnly = new System.Windows.Forms.CheckBox();
            this.checkBoxShowAll = new System.Windows.Forms.CheckBox();
            this.groupBoxMods = new System.Windows.Forms.GroupBox();
            this.dataGridViewMods = new System.Windows.Forms.DataGridView();
            this.columnEnabled = new System.Windows.Forms.DataGridViewCheckBoxColumn();
            this.columnModName = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.columnCategory = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.columnTier = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.columnStatus = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.columnSuggestedAction = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.panelSpacer = new System.Windows.Forms.Panel();
            this.groupBoxHeatmap = new System.Windows.Forms.GroupBox();
            this.panelHeatmapScroll = new System.Windows.Forms.Panel();
            this.flowHeatmap = new System.Windows.Forms.FlowLayoutPanel();
            this.flowLegend = new System.Windows.Forms.FlowLayoutPanel();
            this.legendCritical = new System.Windows.Forms.Label();
            this.legendHigh = new System.Windows.Forms.Label();
            this.legendLow = new System.Windows.Forms.Label();
            this.legendRedundant = new System.Windows.Forms.Label();
            this.legendDisabled = new System.Windows.Forms.Label();
            this.legendOk = new System.Windows.Forms.Label();
            this.toolTipHeatmap = new System.Windows.Forms.ToolTip(this.components);
            this.tableMain.SuspendLayout();
            this.panelTop.SuspendLayout();
            this.tableTop.SuspendLayout();
            this.flowTopActions.SuspendLayout();
            this.flowControlFilters.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.trackBarSeverity)).BeginInit();
            this.groupBoxMods.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridViewMods)).BeginInit();
            this.groupBoxHeatmap.SuspendLayout();
            this.panelHeatmapScroll.SuspendLayout();
            this.flowLegend.SuspendLayout();
            this.SuspendLayout();
            // 
            // tableMain
            // 
            this.tableMain.ColumnCount = 1;
            this.tableMain.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.tableMain.Controls.Add(this.panelTop, 0, 0);
            this.tableMain.Controls.Add(this.groupBoxMods, 0, 1);
            this.tableMain.Controls.Add(this.panelSpacer, 0, 2);
            this.tableMain.Controls.Add(this.groupBoxHeatmap, 0, 3);
            this.tableMain.Controls.Add(this.flowLegend, 0, 4);
            this.tableMain.Dock = System.Windows.Forms.DockStyle.Fill;
            this.tableMain.Location = new System.Drawing.Point(0, 0);
            this.tableMain.Name = "tableMain";
            this.tableMain.RowCount = 5;
            this.tableMain.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 240F));
            this.tableMain.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.tableMain.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 8F));
            this.tableMain.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 240F));
            this.tableMain.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 34F));
            this.tableMain.Size = new System.Drawing.Size(2139, 983);
            this.tableMain.TabIndex = 0;
            // 
            // panelTop
            // 
            this.panelTop.Controls.Add(this.tableTop);
            this.panelTop.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelTop.Location = new System.Drawing.Point(6, 6);
            this.panelTop.Margin = new System.Windows.Forms.Padding(6);
            this.panelTop.Name = "panelTop";
            this.panelTop.Padding = new System.Windows.Forms.Padding(8);
            this.panelTop.Size = new System.Drawing.Size(2127, 228);
            this.panelTop.TabIndex = 0;
            this.panelTop.Paint += new System.Windows.Forms.PaintEventHandler(this.panelTop_Paint);
            // 
            // tableTop
            // 
            this.tableTop.ColumnCount = 1;
            this.tableTop.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.tableTop.Controls.Add(this.flowTopActions, 0, 0);
            this.tableTop.Controls.Add(this.flowControlFilters, 0, 2);
            this.tableTop.Dock = System.Windows.Forms.DockStyle.Fill;
            this.tableTop.Location = new System.Drawing.Point(8, 8);
            this.tableTop.Name = "tableTop";
            this.tableTop.RowCount = 3;
            this.tableTop.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 140F));
            this.tableTop.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 11F));
            this.tableTop.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 58F));
            this.tableTop.Size = new System.Drawing.Size(2111, 212);
            this.tableTop.TabIndex = 0;
            // 
            // flowTopActions
            // 
            this.flowTopActions.Controls.Add(this.buttonScanMods);
            this.flowTopActions.Controls.Add(this.buttonGenerateApplyLoadOrder);
            this.flowTopActions.Controls.Add(this.buttonExportLoadOrder);
            this.flowTopActions.Controls.Add(this.buttonRenameFolder);
            this.flowTopActions.Controls.Add(this.buttonExplainIssues);
            this.flowTopActions.Controls.Add(this.buttonResolveConflicts);
            this.flowTopActions.Controls.Add(this.buttonFindDuplicates);
            this.flowTopActions.Controls.Add(this.buttonApplyUpdateFixes);
            this.flowTopActions.Controls.Add(this.buttonExplainSelected);
            this.flowTopActions.Controls.Add(this.buttonDiagnoseVisibility);
            this.flowTopActions.Controls.Add(this.buttonFilterOK);
            this.flowTopActions.Controls.Add(this.buttonFilterDisabled);
            this.flowTopActions.Controls.Add(this.buttonFilterRedundant);
            this.flowTopActions.Controls.Add(this.buttonFilterLow);
            this.flowTopActions.Controls.Add(this.buttonFilterHigh);
            this.flowTopActions.Controls.Add(this.buttonFilterCritical);
            this.flowTopActions.Controls.Add(this.labelStats);
            this.flowTopActions.Dock = System.Windows.Forms.DockStyle.Top;
            this.flowTopActions.Location = new System.Drawing.Point(3, 3);
            this.flowTopActions.Name = "flowTopActions";
            this.flowTopActions.Padding = new System.Windows.Forms.Padding(8);
            this.flowTopActions.Size = new System.Drawing.Size(2105, 134);
            this.flowTopActions.TabIndex = 0;
            // 
            // buttonScanMods
            // 
            this.buttonScanMods.AutoSize = true;
            this.buttonScanMods.Location = new System.Drawing.Point(14, 14);
            this.buttonScanMods.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonScanMods.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonScanMods.Name = "buttonScanMods";
            this.buttonScanMods.Size = new System.Drawing.Size(246, 38);
            this.buttonScanMods.TabIndex = 0;
            this.buttonScanMods.Text = "Scan Mods";
            this.buttonScanMods.UseVisualStyleBackColor = true;
            this.buttonScanMods.Click += new System.EventHandler(this.buttonScanMods_Click);
            // 
            // buttonGenerateApplyLoadOrder
            // 
            this.buttonGenerateApplyLoadOrder.AutoSize = true;
            this.buttonGenerateApplyLoadOrder.Location = new System.Drawing.Point(272, 14);
            this.buttonGenerateApplyLoadOrder.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonGenerateApplyLoadOrder.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonGenerateApplyLoadOrder.Name = "buttonGenerateApplyLoadOrder";
            this.buttonGenerateApplyLoadOrder.Size = new System.Drawing.Size(316, 38);
            this.buttonGenerateApplyLoadOrder.TabIndex = 1;
            this.buttonGenerateApplyLoadOrder.Text = "Generate + Apply Load Order";
            this.buttonGenerateApplyLoadOrder.UseVisualStyleBackColor = true;
            this.buttonGenerateApplyLoadOrder.Click += new System.EventHandler(this.buttonGenerateApplyLoadOrder_Click);
            // 
            // buttonExportLoadOrder
            // 
            this.buttonExportLoadOrder.AutoSize = true;
            this.buttonExportLoadOrder.Location = new System.Drawing.Point(600, 14);
            this.buttonExportLoadOrder.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonExportLoadOrder.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonExportLoadOrder.Name = "buttonExportLoadOrder";
            this.buttonExportLoadOrder.Size = new System.Drawing.Size(261, 38);
            this.buttonExportLoadOrder.TabIndex = 2;
            this.buttonExportLoadOrder.Text = "Export Load Order";
            this.buttonExportLoadOrder.UseVisualStyleBackColor = true;
            this.buttonExportLoadOrder.Click += new System.EventHandler(this.buttonExportLoadOrder_Click);
            // 
            // buttonRenameFolder
            // 
            this.buttonRenameFolder.AutoSize = true;
            this.buttonRenameFolder.Location = new System.Drawing.Point(873, 14);
            this.buttonRenameFolder.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonRenameFolder.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonRenameFolder.Name = "buttonRenameFolder";
            this.buttonRenameFolder.Size = new System.Drawing.Size(256, 38);
            this.buttonRenameFolder.TabIndex = 3;
            this.buttonRenameFolder.Text = "Rename Folder";
            this.buttonRenameFolder.UseVisualStyleBackColor = true;
            this.buttonRenameFolder.Click += new System.EventHandler(this.buttonRenameFolder_Click);
            // 
            // buttonExplainIssues
            // 
            this.buttonExplainIssues.AutoSize = true;
            this.buttonExplainIssues.Location = new System.Drawing.Point(1141, 14);
            this.buttonExplainIssues.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonExplainIssues.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonExplainIssues.Name = "buttonExplainIssues";
            this.buttonExplainIssues.Size = new System.Drawing.Size(326, 38);
            this.buttonExplainIssues.TabIndex = 4;
            this.buttonExplainIssues.Text = "Explain Issues (Plain English)";
            this.buttonExplainIssues.UseVisualStyleBackColor = true;
            this.buttonExplainIssues.Click += new System.EventHandler(this.buttonExplainIssues_Click);
            // 
            // buttonResolveConflicts
            // 
            this.buttonResolveConflicts.AutoSize = true;
            this.buttonResolveConflicts.Location = new System.Drawing.Point(1479, 14);
            this.buttonResolveConflicts.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonResolveConflicts.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonResolveConflicts.Name = "buttonResolveConflicts";
            this.buttonResolveConflicts.Size = new System.Drawing.Size(346, 38);
            this.buttonResolveConflicts.TabIndex = 5;
            this.buttonResolveConflicts.Text = "Resolve Conflicts (Patch / Rules)";
            this.buttonResolveConflicts.UseVisualStyleBackColor = true;
            this.buttonResolveConflicts.Click += new System.EventHandler(this.buttonResolveConflicts_Click);
            // 
            // buttonFindDuplicates
            // 
            this.buttonFindDuplicates.AutoSize = true;
            this.buttonFindDuplicates.Location = new System.Drawing.Point(14, 65);
            this.buttonFindDuplicates.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFindDuplicates.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFindDuplicates.Name = "buttonFindDuplicates";
            this.buttonFindDuplicates.Size = new System.Drawing.Size(306, 38);
            this.buttonFindDuplicates.TabIndex = 6;
            this.buttonFindDuplicates.Text = "Find Duplicates (Updates)";
            this.buttonFindDuplicates.UseVisualStyleBackColor = true;
            this.buttonFindDuplicates.Click += new System.EventHandler(this.buttonFindDuplicates_Click);
            // 
            // buttonApplyUpdateFixes
            // 
            this.buttonApplyUpdateFixes.AutoSize = true;
            this.buttonApplyUpdateFixes.Location = new System.Drawing.Point(332, 65);
            this.buttonApplyUpdateFixes.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonApplyUpdateFixes.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonApplyUpdateFixes.Name = "buttonApplyUpdateFixes";
            this.buttonApplyUpdateFixes.Size = new System.Drawing.Size(276, 38);
            this.buttonApplyUpdateFixes.TabIndex = 7;
            this.buttonApplyUpdateFixes.Text = "Apply Update Fixes";
            this.buttonApplyUpdateFixes.UseVisualStyleBackColor = true;
            this.buttonApplyUpdateFixes.Click += new System.EventHandler(this.buttonApplyUpdateFixes_Click);
            // 
            // buttonExplainSelected
            // 
            this.buttonExplainSelected.AutoSize = true;
            this.buttonExplainSelected.Location = new System.Drawing.Point(620, 65);
            this.buttonExplainSelected.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonExplainSelected.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonExplainSelected.Name = "buttonExplainSelected";
            this.buttonExplainSelected.Size = new System.Drawing.Size(331, 38);
            this.buttonExplainSelected.TabIndex = 8;
            this.buttonExplainSelected.Text = "Explain Selected (Plain English)";
            this.buttonExplainSelected.UseVisualStyleBackColor = true;
            this.buttonExplainSelected.Click += new System.EventHandler(this.buttonExplainSelected_Click);
            // 
            // buttonDiagnoseVisibility
            // 
            this.buttonDiagnoseVisibility.AutoSize = true;
            this.buttonDiagnoseVisibility.Location = new System.Drawing.Point(963, 65);
            this.buttonDiagnoseVisibility.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonDiagnoseVisibility.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonDiagnoseVisibility.Name = "buttonDiagnoseVisibility";
            this.buttonDiagnoseVisibility.Size = new System.Drawing.Size(281, 38);
            this.buttonDiagnoseVisibility.TabIndex = 9;
            this.buttonDiagnoseVisibility.Text = "Diagnose Visibility";
            this.buttonDiagnoseVisibility.UseVisualStyleBackColor = true;
            this.buttonDiagnoseVisibility.Click += new System.EventHandler(this.buttonDiagnoseVisibility_Click);
            // 
            // buttonFilterOK
            // 
            this.buttonFilterOK.Location = new System.Drawing.Point(1256, 65);
            this.buttonFilterOK.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFilterOK.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterOK.Name = "buttonFilterOK";
            this.buttonFilterOK.Size = new System.Drawing.Size(131, 23);
            this.buttonFilterOK.TabIndex = 6;
            this.buttonFilterOK.Text = "OK (0)";
            this.buttonFilterOK.UseVisualStyleBackColor = true;
            this.buttonFilterOK.Click += new System.EventHandler(this.buttonFilterOK_Click);
            // 
            // buttonFilterDisabled
            // 
            this.buttonFilterDisabled.Location = new System.Drawing.Point(1399, 65);
            this.buttonFilterDisabled.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFilterDisabled.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterDisabled.Name = "buttonFilterDisabled";
            this.buttonFilterDisabled.Size = new System.Drawing.Size(127, 23);
            this.buttonFilterDisabled.TabIndex = 5;
            this.buttonFilterDisabled.Text = "Disabled (0)";
            this.buttonFilterDisabled.UseVisualStyleBackColor = true;
            this.buttonFilterDisabled.Click += new System.EventHandler(this.buttonFilterDisabled_Click);
            // 
            // buttonFilterRedundant
            // 
            this.buttonFilterRedundant.Location = new System.Drawing.Point(1538, 65);
            this.buttonFilterRedundant.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFilterRedundant.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterRedundant.Name = "buttonFilterRedundant";
            this.buttonFilterRedundant.Size = new System.Drawing.Size(132, 23);
            this.buttonFilterRedundant.TabIndex = 4;
            this.buttonFilterRedundant.Text = "Redundant (0)";
            this.buttonFilterRedundant.UseVisualStyleBackColor = true;
            this.buttonFilterRedundant.Click += new System.EventHandler(this.buttonFilterRedundant_Click);
            // 
            // buttonFilterLow
            // 
            this.buttonFilterLow.Location = new System.Drawing.Point(1682, 65);
            this.buttonFilterLow.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFilterLow.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterLow.Name = "buttonFilterLow";
            this.buttonFilterLow.Size = new System.Drawing.Size(127, 23);
            this.buttonFilterLow.TabIndex = 3;
            this.buttonFilterLow.Text = "Low (0)";
            this.buttonFilterLow.UseVisualStyleBackColor = true;
            this.buttonFilterLow.Click += new System.EventHandler(this.buttonFilterLow_Click);
            // 
            // buttonFilterHigh
            // 
            this.buttonFilterHigh.Location = new System.Drawing.Point(1821, 65);
            this.buttonFilterHigh.Margin = new System.Windows.Forms.Padding(6, 6, 6, 7);
            this.buttonFilterHigh.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterHigh.Name = "buttonFilterHigh";
            this.buttonFilterHigh.Size = new System.Drawing.Size(127, 23);
            this.buttonFilterHigh.TabIndex = 2;
            this.buttonFilterHigh.Text = "High (0)";
            this.buttonFilterHigh.UseVisualStyleBackColor = true;
            this.buttonFilterHigh.Click += new System.EventHandler(this.buttonFilterHigh_Click);
            // 
            // buttonFilterCritical
            // 
            this.buttonFilterCritical.Location = new System.Drawing.Point(1960, 65);
            this.buttonFilterCritical.Margin = new System.Windows.Forms.Padding(6);
            this.buttonFilterCritical.MinimumSize = new System.Drawing.Size(90, 0);
            this.buttonFilterCritical.Name = "buttonFilterCritical";
            this.buttonFilterCritical.Size = new System.Drawing.Size(127, 23);
            this.buttonFilterCritical.TabIndex = 1;
            this.buttonFilterCritical.Text = "Critical (0)";
            this.buttonFilterCritical.UseVisualStyleBackColor = true;
            this.buttonFilterCritical.Click += new System.EventHandler(this.buttonFilterCritical_Click);
            // 
            // labelStats
            // 
            this.labelStats.AutoSize = true;
            this.labelStats.Location = new System.Drawing.Point(11, 113);
            this.labelStats.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.labelStats.Name = "labelStats";
            this.labelStats.Size = new System.Drawing.Size(164, 13);
            this.labelStats.TabIndex = 0;
            this.labelStats.Text = "Mods: 0 | Enabled: 0 | Conflicts: 0";
            // 
            // flowControlFilters
            // 
            this.flowControlFilters.AutoScroll = true;
            this.flowControlFilters.Controls.Add(this.labelCategory);
            this.flowControlFilters.Controls.Add(this.comboBoxCategory);
            this.flowControlFilters.Controls.Add(this.labelSeverity);
            this.flowControlFilters.Controls.Add(this.trackBarSeverity);
            this.flowControlFilters.Controls.Add(this.checkBoxConflictsOnly);
            this.flowControlFilters.Controls.Add(this.checkBoxShowAll);
            this.flowControlFilters.Dock = System.Windows.Forms.DockStyle.Fill;
            this.flowControlFilters.Location = new System.Drawing.Point(3, 154);
            this.flowControlFilters.Name = "flowControlFilters";
            this.flowControlFilters.Padding = new System.Windows.Forms.Padding(8);
            this.flowControlFilters.Size = new System.Drawing.Size(2105, 55);
            this.flowControlFilters.TabIndex = 2;
            // 
            // labelCategory
            // 
            this.labelCategory.AutoSize = true;
            this.labelCategory.Location = new System.Drawing.Point(14, 12);
            this.labelCategory.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.labelCategory.Name = "labelCategory";
            this.labelCategory.Size = new System.Drawing.Size(52, 13);
            this.labelCategory.TabIndex = 7;
            this.labelCategory.Text = "Category:";
            // 
            // comboBoxCategory
            // 
            this.comboBoxCategory.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.comboBoxCategory.FormattingEnabled = true;
            this.comboBoxCategory.Items.AddRange(new object[] {
            "All"});
            this.comboBoxCategory.Location = new System.Drawing.Point(78, 12);
            this.comboBoxCategory.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.comboBoxCategory.MinimumSize = new System.Drawing.Size(140, 0);
            this.comboBoxCategory.Name = "comboBoxCategory";
            this.comboBoxCategory.Size = new System.Drawing.Size(140, 21);
            this.comboBoxCategory.TabIndex = 8;
            this.comboBoxCategory.SelectedIndexChanged += new System.EventHandler(this.comboBoxCategory_SelectedIndexChanged);
            // 
            // labelSeverity
            // 
            this.labelSeverity.AutoSize = true;
            this.labelSeverity.Location = new System.Drawing.Point(230, 12);
            this.labelSeverity.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.labelSeverity.Name = "labelSeverity";
            this.labelSeverity.Size = new System.Drawing.Size(48, 13);
            this.labelSeverity.TabIndex = 9;
            this.labelSeverity.Text = "Severity:";
            // 
            // trackBarSeverity
            // 
            this.trackBarSeverity.Location = new System.Drawing.Point(290, 12);
            this.trackBarSeverity.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.trackBarSeverity.Maximum = 100;
            this.trackBarSeverity.Name = "trackBarSeverity";
            this.trackBarSeverity.Size = new System.Drawing.Size(120, 45);
            this.trackBarSeverity.TabIndex = 10;
            this.trackBarSeverity.TickStyle = System.Windows.Forms.TickStyle.None;
            this.trackBarSeverity.ValueChanged += new System.EventHandler(this.trackBarSeverity_ValueChanged);
            // 
            // checkBoxConflictsOnly
            // 
            this.checkBoxConflictsOnly.AutoSize = true;
            this.checkBoxConflictsOnly.Location = new System.Drawing.Point(422, 12);
            this.checkBoxConflictsOnly.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.checkBoxConflictsOnly.Name = "checkBoxConflictsOnly";
            this.checkBoxConflictsOnly.Size = new System.Drawing.Size(88, 17);
            this.checkBoxConflictsOnly.TabIndex = 11;
            this.checkBoxConflictsOnly.Text = "Conflicts only";
            this.checkBoxConflictsOnly.UseVisualStyleBackColor = true;
            this.checkBoxConflictsOnly.CheckedChanged += new System.EventHandler(this.checkBoxConflictsOnly_CheckedChanged);
            // 
            // checkBoxShowAll
            // 
            this.checkBoxShowAll.AutoSize = true;
            this.checkBoxShowAll.Location = new System.Drawing.Point(522, 12);
            this.checkBoxShowAll.Margin = new System.Windows.Forms.Padding(6, 4, 6, 4);
            this.checkBoxShowAll.Name = "checkBoxShowAll";
            this.checkBoxShowAll.Size = new System.Drawing.Size(132, 17);
            this.checkBoxShowAll.TabIndex = 12;
            this.checkBoxShowAll.Text = "Show All (ignore filters)";
            this.checkBoxShowAll.UseVisualStyleBackColor = true;
            this.checkBoxShowAll.CheckedChanged += new System.EventHandler(this.checkBoxShowAll_CheckedChanged);
            // 
            // groupBoxMods
            // 
            this.groupBoxMods.Controls.Add(this.dataGridViewMods);
            this.groupBoxMods.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxMods.Location = new System.Drawing.Point(10, 250);
            this.groupBoxMods.Margin = new System.Windows.Forms.Padding(10);
            this.groupBoxMods.Name = "groupBoxMods";
            this.groupBoxMods.Size = new System.Drawing.Size(2119, 441);
            this.groupBoxMods.TabIndex = 1;
            this.groupBoxMods.TabStop = false;
            this.groupBoxMods.Text = "Mods";
            // 
            // dataGridViewMods
            // 
            this.dataGridViewMods.AllowUserToAddRows = false;
            this.dataGridViewMods.AllowUserToDeleteRows = false;
            this.dataGridViewMods.AllowUserToResizeRows = false;
            this.dataGridViewMods.BackgroundColor = System.Drawing.Color.FromArgb(((int)(((byte)(25)))), ((int)(((byte)(25)))), ((int)(((byte)(25)))));
            this.dataGridViewMods.BorderStyle = System.Windows.Forms.BorderStyle.None;
            this.dataGridViewMods.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.dataGridViewMods.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.columnEnabled,
            this.columnModName,
            this.columnCategory,
            this.columnTier,
            this.columnStatus,
            this.columnSuggestedAction});
            this.dataGridViewMods.Dock = System.Windows.Forms.DockStyle.Fill;
            this.dataGridViewMods.GridColor = System.Drawing.Color.FromArgb(((int)(((byte)(64)))), ((int)(((byte)(64)))), ((int)(((byte)(64)))));
            this.dataGridViewMods.Location = new System.Drawing.Point(3, 16);
            this.dataGridViewMods.MultiSelect = false;
            this.dataGridViewMods.Name = "dataGridViewMods";
            this.dataGridViewMods.ReadOnly = true;
            this.dataGridViewMods.RowHeadersVisible = false;
            this.dataGridViewMods.SelectionMode = System.Windows.Forms.DataGridViewSelectionMode.FullRowSelect;
            this.dataGridViewMods.Size = new System.Drawing.Size(2113, 422);
            this.dataGridViewMods.TabIndex = 0;
            this.dataGridViewMods.CellContentClick += new System.Windows.Forms.DataGridViewCellEventHandler(this.dataGridViewMods_CellContentClick);
            // 
            // columnEnabled
            // 
            this.columnEnabled.HeaderText = "Enabled";
            this.columnEnabled.Name = "columnEnabled";
            this.columnEnabled.ReadOnly = true;
            this.columnEnabled.Width = 70;
            // 
            // columnModName
            // 
            this.columnModName.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.Fill;
            this.columnModName.HeaderText = "Mod";
            this.columnModName.MinimumWidth = 200;
            this.columnModName.Name = "columnModName";
            this.columnModName.ReadOnly = true;
            // 
            // columnCategory
            // 
            this.columnCategory.HeaderText = "Category";
            this.columnCategory.Name = "columnCategory";
            this.columnCategory.ReadOnly = true;
            this.columnCategory.Width = 140;
            // 
            // columnTier
            // 
            this.columnTier.HeaderText = "Tier";
            this.columnTier.Name = "columnTier";
            this.columnTier.ReadOnly = true;
            this.columnTier.Width = 80;
            // 
            // columnStatus
            // 
            this.columnStatus.HeaderText = "Status";
            this.columnStatus.Name = "columnStatus";
            this.columnStatus.ReadOnly = true;
            this.columnStatus.Width = 140;
            // 
            // columnSuggestedAction
            // 
            this.columnSuggestedAction.HeaderText = "Suggested";
            this.columnSuggestedAction.Name = "columnSuggestedAction";
            this.columnSuggestedAction.ReadOnly = true;
            this.columnSuggestedAction.Width = 220;
            // 
            // panelSpacer
            // 
            this.panelSpacer.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelSpacer.Location = new System.Drawing.Point(3, 704);
            this.panelSpacer.Name = "panelSpacer";
            this.panelSpacer.Size = new System.Drawing.Size(2133, 2);
            this.panelSpacer.TabIndex = 2;
            // 
            // groupBoxHeatmap
            // 
            this.groupBoxHeatmap.Controls.Add(this.panelHeatmapScroll);
            this.groupBoxHeatmap.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBoxHeatmap.Location = new System.Drawing.Point(10, 719);
            this.groupBoxHeatmap.Margin = new System.Windows.Forms.Padding(10);
            this.groupBoxHeatmap.MinimumSize = new System.Drawing.Size(300, 200);
            this.groupBoxHeatmap.Name = "groupBoxHeatmap";
            this.groupBoxHeatmap.Size = new System.Drawing.Size(2119, 220);
            this.groupBoxHeatmap.TabIndex = 3;
            this.groupBoxHeatmap.TabStop = false;
            this.groupBoxHeatmap.Text = "Risk Heatmap";
            // 
            // panelHeatmapScroll
            // 
            this.panelHeatmapScroll.AutoScroll = true;
            this.panelHeatmapScroll.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.panelHeatmapScroll.Controls.Add(this.flowHeatmap);
            this.panelHeatmapScroll.Dock = System.Windows.Forms.DockStyle.Fill;
            this.panelHeatmapScroll.Location = new System.Drawing.Point(3, 16);
            this.panelHeatmapScroll.Name = "panelHeatmapScroll";
            this.panelHeatmapScroll.Size = new System.Drawing.Size(2113, 201);
            this.panelHeatmapScroll.TabIndex = 0;
            // 
            // flowHeatmap
            // 
            this.flowHeatmap.AutoSize = true;
            this.flowHeatmap.Dock = System.Windows.Forms.DockStyle.Top;
            this.flowHeatmap.Location = new System.Drawing.Point(0, 0);
            this.flowHeatmap.Name = "flowHeatmap";
            this.flowHeatmap.Padding = new System.Windows.Forms.Padding(6);
            this.flowHeatmap.Size = new System.Drawing.Size(2111, 12);
            this.flowHeatmap.TabIndex = 0;
            this.flowHeatmap.ControlAdded += new System.Windows.Forms.ControlEventHandler(this.flowHeatmap_ControlAdded);
            this.flowHeatmap.Paint += new System.Windows.Forms.PaintEventHandler(this.flowHeatmap_Paint);
            // 
            // flowLegend
            // 
            this.flowLegend.Controls.Add(this.legendCritical);
            this.flowLegend.Controls.Add(this.legendHigh);
            this.flowLegend.Controls.Add(this.legendLow);
            this.flowLegend.Controls.Add(this.legendRedundant);
            this.flowLegend.Controls.Add(this.legendDisabled);
            this.flowLegend.Controls.Add(this.legendOk);
            this.flowLegend.Dock = System.Windows.Forms.DockStyle.Fill;
            this.flowLegend.Location = new System.Drawing.Point(3, 952);
            this.flowLegend.Name = "flowLegend";
            this.flowLegend.Padding = new System.Windows.Forms.Padding(6);
            this.flowLegend.Size = new System.Drawing.Size(2133, 28);
            this.flowLegend.TabIndex = 4;
            this.flowLegend.WrapContents = false;
            // 
            // legendCritical
            // 
            this.legendCritical.AutoSize = true;
            this.legendCritical.Location = new System.Drawing.Point(9, 9);
            this.legendCritical.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendCritical.Name = "legendCritical";
            this.legendCritical.Size = new System.Drawing.Size(75, 13);
            this.legendCritical.TabIndex = 0;
            this.legendCritical.Text = "Critical → Red";
            // 
            // legendHigh
            // 
            this.legendHigh.AutoSize = true;
            this.legendHigh.Location = new System.Drawing.Point(99, 9);
            this.legendHigh.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendHigh.Name = "legendHigh";
            this.legendHigh.Size = new System.Drawing.Size(81, 13);
            this.legendHigh.TabIndex = 1;
            this.legendHigh.Text = "High → Orange";
            // 
            // legendLow
            // 
            this.legendLow.AutoSize = true;
            this.legendLow.Location = new System.Drawing.Point(195, 9);
            this.legendLow.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendLow.Name = "legendLow";
            this.legendLow.Size = new System.Drawing.Size(75, 13);
            this.legendLow.TabIndex = 2;
            this.legendLow.Text = "Low → Yellow";
            // 
            // legendRedundant
            // 
            this.legendRedundant.AutoSize = true;
            this.legendRedundant.Location = new System.Drawing.Point(285, 9);
            this.legendRedundant.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendRedundant.Name = "legendRedundant";
            this.legendRedundant.Size = new System.Drawing.Size(98, 13);
            this.legendRedundant.TabIndex = 3;
            this.legendRedundant.Text = "Redundant → Blue";
            // 
            // legendDisabled
            // 
            this.legendDisabled.AutoSize = true;
            this.legendDisabled.Location = new System.Drawing.Point(398, 9);
            this.legendDisabled.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendDisabled.Name = "legendDisabled";
            this.legendDisabled.Size = new System.Drawing.Size(87, 13);
            this.legendDisabled.TabIndex = 4;
            this.legendDisabled.Text = "Disabled → Gray";
            // 
            // legendOk
            // 
            this.legendOk.AutoSize = true;
            this.legendOk.Location = new System.Drawing.Point(500, 9);
            this.legendOk.Margin = new System.Windows.Forms.Padding(3, 3, 12, 3);
            this.legendOk.Name = "legendOk";
            this.legendOk.Size = new System.Drawing.Size(68, 13);
            this.legendOk.TabIndex = 5;
            this.legendOk.Text = "OK → Green";
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(2139, 983);
            this.Controls.Add(this.tableMain);
            this.MinimumSize = new System.Drawing.Size(1280, 720);
            this.Name = "Form1";
            this.Text = "s";
            this.Load += new System.EventHandler(this.Form1_Load);
            this.tableMain.ResumeLayout(false);
            this.panelTop.ResumeLayout(false);
            this.tableTop.ResumeLayout(false);
            this.flowTopActions.ResumeLayout(false);
            this.flowTopActions.PerformLayout();
            this.flowControlFilters.ResumeLayout(false);
            this.flowControlFilters.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.trackBarSeverity)).EndInit();
            this.groupBoxMods.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.dataGridViewMods)).EndInit();
            this.groupBoxHeatmap.ResumeLayout(false);
            this.panelHeatmapScroll.ResumeLayout(false);
            this.panelHeatmapScroll.PerformLayout();
            this.flowLegend.ResumeLayout(false);
            this.flowLegend.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.TableLayoutPanel tableMain;
        private System.Windows.Forms.Panel panelSpacer;
        private System.Windows.Forms.GroupBox groupBoxHeatmap;
        private System.Windows.Forms.Panel panelHeatmapScroll;
        private System.Windows.Forms.FlowLayoutPanel flowHeatmap;
        private System.Windows.Forms.ToolTip toolTipHeatmap;
        private System.Windows.Forms.FlowLayoutPanel flowLegend;
        private System.Windows.Forms.Label legendCritical;
        private System.Windows.Forms.Label legendHigh;
        private System.Windows.Forms.Label legendLow;
        private System.Windows.Forms.Label legendRedundant;
        private System.Windows.Forms.Label legendDisabled;
        private System.Windows.Forms.Label legendOk;
        private System.Windows.Forms.Panel panelTop;
        private System.Windows.Forms.TableLayoutPanel tableTop;
        private System.Windows.Forms.FlowLayoutPanel flowTopActions;
        private System.Windows.Forms.Button buttonScanMods;
        private System.Windows.Forms.Button buttonGenerateApplyLoadOrder;
        private System.Windows.Forms.Button buttonExportLoadOrder;
        private System.Windows.Forms.Button buttonRenameFolder;
        private System.Windows.Forms.Button buttonExplainIssues;
        private System.Windows.Forms.Button buttonResolveConflicts;
        private System.Windows.Forms.Button buttonFindDuplicates;
        private System.Windows.Forms.Button buttonApplyUpdateFixes;
        private System.Windows.Forms.Button buttonExplainSelected;
        private System.Windows.Forms.Button buttonDiagnoseVisibility;
        private System.Windows.Forms.Label labelStats;
        private System.Windows.Forms.Button buttonFilterCritical;
        private System.Windows.Forms.Button buttonFilterHigh;
        private System.Windows.Forms.Button buttonFilterLow;
        private System.Windows.Forms.Button buttonFilterRedundant;
        private System.Windows.Forms.Button buttonFilterDisabled;
        private System.Windows.Forms.Button buttonFilterOK;
        private System.Windows.Forms.FlowLayoutPanel flowControlFilters;
        private System.Windows.Forms.Label labelCategory;
        private System.Windows.Forms.ComboBox comboBoxCategory;
        private System.Windows.Forms.Label labelSeverity;
        private System.Windows.Forms.TrackBar trackBarSeverity;
        private System.Windows.Forms.CheckBox checkBoxConflictsOnly;
        private System.Windows.Forms.CheckBox checkBoxShowAll;
        private System.Windows.Forms.GroupBox groupBoxMods;
        private System.Windows.Forms.DataGridView dataGridViewMods;
        private System.Windows.Forms.DataGridViewCheckBoxColumn columnEnabled;
        private System.Windows.Forms.DataGridViewTextBoxColumn columnModName;
        private System.Windows.Forms.DataGridViewTextBoxColumn columnCategory;
        private System.Windows.Forms.DataGridViewTextBoxColumn columnTier;
        private System.Windows.Forms.DataGridViewTextBoxColumn columnStatus;
        private System.Windows.Forms.DataGridViewTextBoxColumn columnSuggestedAction;
    }
}

