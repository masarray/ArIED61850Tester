from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def sub_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    if replacement in text:
        return text
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return updated


xaml_path = "MainWindow.xaml"
xaml = read(xaml_path)

xaml = sub_once(
    xaml,
    r'''        <Grid\.RowDefinitions>\s*<RowDefinition Height="Auto"/>\s*<RowDefinition Height="Auto"/>\s*<RowDefinition Height="\*"/>\s*<RowDefinition Height="Auto"/>\s*</Grid\.RowDefinitions>''',
    '''        <Grid.RowDefinitions>\n            <RowDefinition Height="Auto"/>\n            <RowDefinition Height="*"/>\n            <RowDefinition Height="Auto"/>\n        </Grid.RowDefinitions>''',
    "main grid rows",
    re.S)

if "Compact navigation row: the large top application bar is removed" not in xaml:
    pattern = (
        r'''\n        <!-- Premium compact application bar.*?-->\n'''
        r'''        <Grid Grid.Row="0" Height="44" Margin="0,0,0,10">.*?\n        </Grid>\n\n'''
        r'''        <!-- Restored premium segmented navigation.*?-->\n'''
        r'''        <Grid Grid.Row="1"''')
    replacement = '''\n        <!-- Compact navigation row: the large top application bar is removed to free vertical space. -->\n        <Grid Grid.Row="0"'''
    xaml = sub_once(xaml, pattern, replacement, "top application bar", re.S)

xaml = xaml.replace('<TabControl x:Name="MainTabs" Grid.Row="2"', '<TabControl x:Name="MainTabs" Grid.Row="1"', 1)
xaml = xaml.replace('<Border Grid.Row="3" Margin="0,10,0,0"', '<Border Grid.Row="2" Margin="0,10,0,0"', 1)

if 'ToolTip="Open ArIED project"' not in xaml:
    pattern = (
        r'''                            <Grid DockPanel\.Dock="Top" Margin="0,0,0,8">\s*'''
        r'''<StackPanel Orientation="Horizontal">\s*'''
        r'''<Ellipse Width="8" Height="8" Fill="\{StaticResource Accent\}" Margin="0,0,8,0" VerticalAlignment="Center"/>\s*'''
        r'''<TextBlock Text="IED Explorer" FontSize="15\.5" FontWeight="SemiBold" Foreground="\{StaticResource Ink\}"/>\s*'''
        r'''</StackPanel>\s*</Grid>''')
    replacement = '''                            <Grid DockPanel.Dock="Top" Margin="0,0,0,8">\n                                <Grid.ColumnDefinitions>\n                                    <ColumnDefinition Width="*"/>\n                                    <ColumnDefinition Width="Auto"/>\n                                </Grid.ColumnDefinitions>\n                                <StackPanel Orientation="Horizontal">\n                                    <Ellipse Width="8" Height="8" Fill="{StaticResource Accent}" Margin="0,0,8,0" VerticalAlignment="Center"/>\n                                    <TextBlock Text="IED Explorer" FontSize="15.5" FontWeight="SemiBold" Foreground="{StaticResource Ink}" VerticalAlignment="Center"/>\n                                </StackPanel>\n                                <StackPanel Grid.Column="1" Orientation="Horizontal" HorizontalAlignment="Right">\n                                    <Button Style="{StaticResource IedIconButton}" Click="OpenProject_Click" ToolTip="Open ArIED project" Margin="0,0,6,0">\n                                        <Viewbox Width="16" Height="16"><Canvas Width="24" Height="24">\n                                            <Path Data="M4,7 H10 L12,9 H20 V20 H4 Z M4,7 V5 H10 L12,7" Stroke="#2563EB" StrokeThickness="1.8" StrokeLineJoin="Round" StrokeStartLineCap="Round" StrokeEndLineCap="Round" Fill="Transparent"/>\n                                        </Canvas></Viewbox>\n                                    </Button>\n                                    <Button Style="{StaticResource IedIconButton}" Click="SaveProject_Click" ToolTip="Save ArIED project">\n                                        <Viewbox Width="16" Height="16"><Canvas Width="24" Height="24">\n                                            <Path Data="M5,4 H17 L20,7 V20 H5 Z M8,4 V9 H16 V4 M9,20 V14 H16 V20" Stroke="#2563EB" StrokeThickness="1.8" StrokeLineJoin="Round" StrokeStartLineCap="Round" StrokeEndLineCap="Round" Fill="Transparent"/>\n                                        </Canvas></Viewbox>\n                                    </Button>\n                                </StackPanel>\n                            </Grid>'''
    xaml = sub_once(xaml, pattern, replacement, "IED Explorer actions", re.S)

if xaml.count('Content="{Binding ControlPendingConfirmationLabel}"') != 1:
    raise SystemExit("P0 guard: stable single Confirm button is missing")
if 'Content="Confirm Open"' in xaml or 'Content="Confirm Close"' in xaml:
    raise SystemExit("P0 guard: legacy dual Confirm buttons detected")
write(xaml_path, xaml)


cs_path = "MainWindow.xaml.cs"
cs = read(cs_path)

if "_autoExpandedCommandDevices" not in cs:
    cs = sub_once(cs, r'''(    private bool _connectAllInProgress;\n)''', r'''\1    private readonly HashSet<string> _autoExpandedCommandDevices = new(StringComparer.OrdinalIgnoreCase);\n''', "command auto-expand state")

if "TryAutoExpandCommandPanelOnce(_selectedDevice);" not in cs:
    cs = sub_once(cs, r'''(            RaiseWorkspaceCounts\(\);\n)(            // ctlModel inspection)''', r'''\1            TryAutoExpandCommandPanelOnce(_selectedDevice);\n\2''', "selected-device expansion hook")

if "SCL model ready. Choose signals" not in cs:
    cs = sub_once(cs, r'''(            AddLog\("INFO", "SCL", status\);\n)''', r'''\1\n            if (firstImported != null && firstImported.Signals.Count > 0)\n            {\n                AddLog("INFO", "SCL", $"{firstImported.Name}: SCL model ready. Choose signals; saving the selection will continue to endpoint binding, connection, and monitoring.");\n                await OpenSignalSelectionWizardAsync(firstImported);\n            }\n''', "Open SCL selection workflow")

if "var allowDynamicReporting = ShouldAllowDynamicReportingForScl(signals);" not in cs:
    cs = sub_once(cs, r'''        device\.AllowDynamicDataSetWrites = false;\n''', '''        var allowDynamicReporting = ShouldAllowDynamicReportingForScl(signals);\n        device.AllowDynamicDataSetWrites = allowDynamicReporting;\n''', "dynamic reporting policy")

if "Smart Dynamic reporting prepared" not in cs:
    pattern = (
        r'''        device\.Status = workspace\.RequiresEndpointBinding \? "SCL model ready — bind endpoint" : "SCL model ready";\n'''
        r'''        device\.Detail = workspace\.RequiresEndpointBinding\n'''
        r'''            \? "LD/LN/DO/DA are available offline\..*?"\n'''
        r'''            : "LD/LN/DO/DA were loaded offline\..*?";\n'''
        r'''        device\.AcquisitionMode = "SCL offline design model";''')
    replacement = '''        device.Status = workspace.RequiresEndpointBinding ? "SCL model ready — bind endpoint" : "SCL model ready";\n        device.Detail = allowDynamicReporting\n            ? (workspace.RequiresEndpointBinding\n                ? "LD/LN/DO/DA are available offline. Static report coverage is incomplete; after signal selection and endpoint binding, ArIED will create an association-scoped dynamic DataSet and use a safe free RCB before polling fallback."\n                : "LD/LN/DO/DA were loaded offline. Static report coverage is incomplete; ArIED will use static coverage where available and create an association-scoped dynamic DataSet for uncovered selected signals before polling fallback.")\n            : (workspace.RequiresEndpointBinding\n                ? "LD/LN/DO/DA are available offline. Press Play to bind an MMS endpoint; no discovery traffic was sent while opening the file."\n                : "LD/LN/DO/DA were loaded offline. Play performs a fast MMS association; Re-scan performs full design-versus-live verification.");\n        device.AcquisitionMode = allowDynamicReporting\n            ? "SCL design • Smart Dynamic reporting prepared"\n            : "SCL offline design model";'''
    cs = sub_once(cs, pattern, replacement, "SCL detail policy", re.S)

if "IsSmartDynamicCapabilityHint" not in cs:
    pattern = r'''    private void LogSclFindings\(string sourceName, IReadOnlyList<SclWorkspaceFinding> findings\)\n    \{.*?\n    \}\n\n    private bool EnsureSclEndpointBinding'''
    replacement = '''    private void LogSclFindings(string sourceName, IReadOnlyList<SclWorkspaceFinding> findings)\n    {\n        var actionableFindings = findings\n            .Where(finding => !IsSmartDynamicCapabilityHint(finding))\n            .ToArray();\n        if (actionableFindings.Length == 0)\n            return;\n\n        var groups = SclFindingAggregator.Group(actionableFindings);\n        if (groups.Count != actionableFindings.Length)\n        {\n            AddLog(\n                "INFO",\n                "SCL",\n                $"{sourceName} • grouped {actionableFindings.Length} actionable finding(s) into {groups.Count} diagnostic group(s). Full typed evidence remains attached to the SCL workspace.");\n        }\n\n        foreach (var group in groups.Take(40))\n        {\n            AddLog(\n                SclFindingAggregator.ToLogLevel(group.Severity),\n                "SCL",\n                $"{sourceName} • {group.Code} [{group.Scope}]: {group.ToDiagnosticMessage()}");\n        }\n\n        if (groups.Count > 40)\n        {\n            var omittedRawCount = groups.Skip(40).Sum(group => group.Count);\n            AddLog(\n                "WARN",\n                "SCL",\n                $"{groups.Count - 40} additional diagnostic group(s), representing {omittedRawCount} actionable finding(s), were omitted from the live log.");\n        }\n\n        if (groups.Any(group => SclFindingAggregator.IsBlockingSeverity(group.Severity)))\n            MarkDiagnosticAlert();\n    }\n\n    private static bool IsSmartDynamicCapabilityHint(SclWorkspaceFinding finding)\n    {\n        if (!finding.Severity.Equals("Warning", StringComparison.OrdinalIgnoreCase))\n            return false;\n\n        return finding.Code.Equals("SCL_REPORT_DATASET_UNASSIGNED", StringComparison.OrdinalIgnoreCase) ||\n               finding.Code.Equals("SCL_REPORT_DATASET_UNRESOLVED", StringComparison.OrdinalIgnoreCase);\n    }\n\n    private static bool ShouldAllowDynamicReportingForScl(IReadOnlyCollection<SignalDefinition> signals)\n    {\n        return signals.Any(signal =>\n            signal.CanPublishAsSignal &&\n            (string.IsNullOrWhiteSpace(signal.DataSetReference) ||\n             string.IsNullOrWhiteSpace(signal.ReportControlReference)));\n    }\n\n    private void TryAutoExpandCommandPanelOnce(Iec61850MonitorDevice? device)\n    {\n        if (device == null || CommandPanelExpander == null || device.CommandSignals.Count == 0)\n            return;\n        if (!_autoExpandedCommandDevices.Add(device.DeviceId))\n            return;\n\n        Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(() =>\n        {\n            if (ReferenceEquals(SelectedDevice, device) && CommandPanelExpander != null)\n                CommandPanelExpander.IsExpanded = true;\n        }));\n    }\n\n    private bool EnsureSclEndpointBinding'''
    cs = sub_once(cs, pattern, replacement, "SCL diagnostic policy", re.S)

if "Saving the selected signals will connect and arm Smart Dynamic reporting" not in cs:
    cs = sub_once(cs, r'''        device\.Detail = "Endpoint bound locally\. Play will fast-connect from the SCL design model; Re-scan performs full comparison\.";''', '''        device.Detail = device.AllowDynamicDataSetWrites\n            ? "Endpoint bound locally. Saving the selected signals will connect and arm Smart Dynamic reporting with a safe free RCB before polling fallback."\n            : "Endpoint bound locally. Play will fast-connect from the SCL design model; Re-scan performs full comparison.";''', "endpoint detail")

if "TryAutoExpandCommandPanelOnce(device);" not in cs:
    cs = sub_once(cs, r'''(        device\.RefreshCommandSignalProjection\(\);\n        RebuildControlFeedbackIndex\(device\);\n)''', r'''\1        TryAutoExpandCommandPanelOnce(device);\n''', "command-ready expansion")

if "? ShouldAllowDynamicReportingForScl(cachedSignals)" not in cs:
    cs = sub_once(cs, r'''                    AllowDynamicDataSetWrites = hasSclProvenance \? false : profile\.AllowDynamicDataSetWrites,''', '''                    AllowDynamicDataSetWrites = hasSclProvenance\n                        ? ShouldAllowDynamicReportingForScl(cachedSignals)\n                        : profile.AllowDynamicDataSetWrites,''', "project restore dynamic policy")

for token in ("TryClaimControlConfirmation", "ControlInspectionBusy", "ControlCommandBusy", "ExecuteClaimedControlAsync"):
    if token not in cs:
        raise SystemExit(f"P0 guard: missing {token}")
if "SclFindingAggregator.Group(actionableFindings)" not in cs:
    raise SystemExit("P1 guard: grouped diagnostics missing")
write(cs_path, cs)


project_path = "ArIED61850Tester.csproj"
project = read(project_path)
for old, new in (("1.6.8.0", "1.6.9.0"), ("1.6.8", "1.6.9")):
    project = project.replace(old, new)
write(project_path, project)

workflow_path = ".github/workflows/build.yml"
workflow = read(workflow_path).replace("-Version 1.6.8", "-Version 1.6.9")
write(workflow_path, workflow)

publish_path = "scripts/publish-windows-portable.ps1"
publish = read(publish_path).replace('"1.6.8"', '"1.6.9"').replace("1.6.8 or v1.6.8", "1.6.9 or v1.6.9")
write(publish_path, publish)

Path("docs/SCL_SMART_DYNAMIC_REPORTING.md").write_text(
    "# SCL-assisted Smart Dynamic reporting\n\n"
    "Opening an SCL file remains offline. After the model is loaded, ArIED opens signal selection immediately. Saving a valid live selection continues to endpoint binding, MMS association, and monitoring.\n\n"
    "Static DataSet and ReportControl coverage is preferred when complete. Missing or partial coverage enables an association-scoped dynamic DataSet for uncovered selected signals and a safe free RCB before polling fallback.\n\n"
    "Unassigned or unresolved report DataSet warnings remain in the typed SCL workspace but are not promoted into noisy live Diagnostics. Positively resolved empty DataSets and other blocking findings remain actionable.\n\n"
    "The command panel expands once per IED only after at least one executable command row is ready.\n",
    encoding="utf-8")
