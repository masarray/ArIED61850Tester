from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source block, found {count}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Main window layout. Keep the P0 single Confirm button untouched.
# ---------------------------------------------------------------------------
xaml_path = "MainWindow.xaml"
xaml = read(xaml_path)

xaml = replace_once(
    xaml,
    '''        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>''',
    '''        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>''',
    "main row definitions")

header_pattern = re.compile(
    r'''\n        <!-- Premium compact application bar restored from the original ArServer shell\. -->\n'''
    r'''        <Grid Grid.Row="0" Height="44" Margin="0,0,0,10">.*?\n        </Grid>\n\n'''
    r'''        <!-- Restored premium segmented navigation\. No global runtime switch: each IED owns its session\. -->\n'''
    r'''        <Grid Grid.Row="1"''',
    re.S)
header_replacement = '''
        <!-- Compact navigation row: the large top application bar is removed to free vertical space. -->
        <Grid Grid.Row="0"'''
if "Compact navigation row: the large top application bar is removed" not in xaml:
    xaml, count = header_pattern.subn(header_replacement, xaml, count=1)
    if count != 1:
        raise SystemExit(f"application header: expected one block, replaced {count}")

xaml = replace_once(
    xaml,
    '<TabControl x:Name="MainTabs" Grid.Row="2" SelectedIndex="0"',
    '<TabControl x:Name="MainTabs" Grid.Row="1" SelectedIndex="0"',
    "main tab row")
xaml = replace_once(
    xaml,
    '<Border Grid.Row="3" Margin="0,10,0,0" Background="#EAF1FF"',
    '<Border Grid.Row="2" Margin="0,10,0,0" Background="#EAF1FF"',
    "status bar row")

explorer_header_old = '''                            <Grid DockPanel.Dock="Top" Margin="0,0,0,8">
                                <StackPanel Orientation="Horizontal">
                                    <Ellipse Width="8" Height="8" Fill="{StaticResource Accent}" Margin="0,0,8,0" VerticalAlignment="Center"/>
                                    <TextBlock Text="IED Explorer" FontSize="15.5" FontWeight="SemiBold" Foreground="{StaticResource Ink}"/>
                                </StackPanel>
                            </Grid>'''
explorer_header_new = '''                            <Grid DockPanel.Dock="Top" Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="*"/>
                                    <ColumnDefinition Width="Auto"/>
                                </Grid.ColumnDefinitions>
                                <StackPanel Orientation="Horizontal">
                                    <Ellipse Width="8" Height="8" Fill="{StaticResource Accent}" Margin="0,0,8,0" VerticalAlignment="Center"/>
                                    <TextBlock Text="IED Explorer" FontSize="15.5" FontWeight="SemiBold" Foreground="{StaticResource Ink}" VerticalAlignment="Center"/>
                                </StackPanel>
                                <StackPanel Grid.Column="1" Orientation="Horizontal" HorizontalAlignment="Right">
                                    <Button Style="{StaticResource IedIconButton}" Click="OpenProject_Click" ToolTip="Open ArIED project" Margin="0,0,6,0">
                                        <Viewbox Width="16" Height="16"><Canvas Width="24" Height="24">
                                            <Path Data="M4,7 H10 L12,9 H20 V20 H4 Z M4,7 V5 H10 L12,7" Stroke="#2563EB" StrokeThickness="1.8" StrokeLineJoin="Round" StrokeStartLineCap="Round" StrokeEndLineCap="Round" Fill="Transparent"/>
                                        </Canvas></Viewbox>
                                    </Button>
                                    <Button Style="{StaticResource IedIconButton}" Click="SaveProject_Click" ToolTip="Save ArIED project">
                                        <Viewbox Width="16" Height="16"><Canvas Width="24" Height="24">
                                            <Path Data="M5,4 H17 L20,7 V20 H5 Z M8,4 V9 H16 V4 M9,20 V14 H16 V20" Stroke="#2563EB" StrokeThickness="1.8" StrokeLineJoin="Round" StrokeStartLineCap="Round" StrokeEndLineCap="Round" Fill="Transparent"/>
                                        </Canvas></Viewbox>
                                    </Button>
                                </StackPanel>
                            </Grid>'''
xaml = replace_once(xaml, explorer_header_old, explorer_header_new, "IED Explorer project actions")

# Guard against the regression that caused the broken patch: P0 must still use one
# stable Confirm button bound to ControlPendingConfirmationLabel.
if xaml.count('Content="{Binding ControlPendingConfirmationLabel}"') != 1:
    raise SystemExit("P0 regression guard: stable single Confirm button is missing")
if 'Content="Confirm Open"' in xaml or 'Content="Confirm Close"' in xaml:
    raise SystemExit("P0 regression guard: legacy dual Confirm buttons detected")

write(xaml_path, xaml)


# ---------------------------------------------------------------------------
# SCL workflow, smart dynamic reporting, quiet capability diagnostics, and
# one-time command panel expansion.
# ---------------------------------------------------------------------------
cs_path = "MainWindow.xaml.cs"
cs = read(cs_path)

cs = replace_once(
    cs,
    '''    private bool _signalSelectionWizardOpen;
    private bool _connectAllInProgress;
''',
    '''    private bool _signalSelectionWizardOpen;
    private bool _connectAllInProgress;
    private readonly HashSet<string> _autoExpandedCommandDevices = new(StringComparer.OrdinalIgnoreCase);
''',
    "one-time command expansion state")

cs = replace_once(
    cs,
    '''            Raise(nameof(ActiveIedTitle));
            Raise(nameof(ActiveIedSubtitle));
            RaiseWorkspaceCounts();
            // ctlModel inspection is preloaded independently of the Expander. Avoid
''',
    '''            Raise(nameof(ActiveIedTitle));
            Raise(nameof(ActiveIedSubtitle));
            RaiseWorkspaceCounts();
            TryAutoExpandCommandPanelOnce(_selectedDevice);
            // ctlModel inspection is preloaded independently of the Expander. Avoid
''',
    "selected-device expansion hook")

cs = replace_once(
    cs,
    '''            var status = $"{sourceName}: {document.Ieds.Count} IED/AP workspace(s), {offlineCount} offline model(s), {endpointCount} MMS endpoint(s) — {added} added, {refreshed} refreshed, {retained} active retained.";
            SetStatus(status);
            AddLog("INFO", "SCL", status);
''',
    '''            var status = $"{sourceName}: {document.Ieds.Count} IED/AP workspace(s), {offlineCount} offline model(s), {endpointCount} MMS endpoint(s) — {added} added, {refreshed} refreshed, {retained} active retained.";
            SetStatus(status);
            AddLog("INFO", "SCL", status);

            if (firstImported != null && firstImported.Signals.Count > 0)
            {
                AddLog("INFO", "SCL", $"{firstImported.Name}: SCL model ready. Choose signals; saving the selection will continue to endpoint binding, connection, and monitoring.");
                await OpenSignalSelectionWizardAsync(firstImported);
            }
''',
    "Open SCL selection workflow")

cs = replace_once(
    cs,
    '''        device.AllowDynamicDataSetWrites = false;
        device.SclWorkspace = workspace;
''',
    '''        var allowDynamicReporting = ShouldAllowDynamicReportingForScl(signals);
        device.AllowDynamicDataSetWrites = allowDynamicReporting;
        device.SclWorkspace = workspace;
''',
    "SCL dynamic reporting policy")

cs = replace_once(
    cs,
    '''        device.Status = workspace.RequiresEndpointBinding ? "SCL model ready — bind endpoint" : "SCL model ready";
        device.Detail = workspace.RequiresEndpointBinding
            ? "LD/LN/DO/DA are available offline. Press Play to bind an MMS endpoint; no discovery traffic was sent while opening the file."
            : "LD/LN/DO/DA were loaded offline. Play performs a fast MMS association; Re-scan performs full design-versus-live verification.";
        device.AcquisitionMode = "SCL offline design model";
''',
    '''        device.Status = workspace.RequiresEndpointBinding ? "SCL model ready — bind endpoint" : "SCL model ready";
        device.Detail = allowDynamicReporting
            ? (workspace.RequiresEndpointBinding
                ? "LD/LN/DO/DA are available offline. Static report coverage is incomplete; after signal selection and endpoint binding, ArIED will create an association-scoped dynamic DataSet and use a safe free RCB before polling fallback."
                : "LD/LN/DO/DA were loaded offline. Static report coverage is incomplete; ArIED will use static coverage where available and create an association-scoped dynamic DataSet for uncovered selected signals before polling fallback.")
            : (workspace.RequiresEndpointBinding
                ? "LD/LN/DO/DA are available offline. Press Play to bind an MMS endpoint; no discovery traffic was sent while opening the file."
                : "LD/LN/DO/DA were loaded offline. Play performs a fast MMS association; Re-scan performs full design-versus-live verification.");
        device.AcquisitionMode = allowDynamicReporting
            ? "SCL design • Smart Dynamic reporting prepared"
            : "SCL offline design model";
''',
    "SCL workspace detail")

log_method_pattern = re.compile(
    r'''    private void LogSclFindings\(string sourceName, IReadOnlyList<SclWorkspaceFinding> findings\)\n    \{.*?\n    \}\n\n    private bool EnsureSclEndpointBinding''',
    re.S)
log_method_new = '''    private void LogSclFindings(string sourceName, IReadOnlyList<SclWorkspaceFinding> findings)
    {
        var actionableFindings = findings
            .Where(finding => !IsSmartDynamicCapabilityHint(finding))
            .ToArray();
        if (actionableFindings.Length == 0)
            return;

        var groups = SclFindingAggregator.Group(actionableFindings);
        if (groups.Count != actionableFindings.Length)
        {
            AddLog(
                "INFO",
                "SCL",
                $"{sourceName} • grouped {actionableFindings.Length} actionable finding(s) into {groups.Count} diagnostic group(s). Full typed evidence remains attached to the SCL workspace.");
        }

        foreach (var group in groups.Take(40))
        {
            AddLog(
                SclFindingAggregator.ToLogLevel(group.Severity),
                "SCL",
                $"{sourceName} • {group.Code} [{group.Scope}]: {group.ToDiagnosticMessage()}");
        }

        if (groups.Count > 40)
        {
            var omittedRawCount = groups
                .Skip(40)
                .Sum(group => group.Count);
            AddLog(
                "WARN",
                "SCL",
                $"{groups.Count - 40} additional diagnostic group(s), representing {omittedRawCount} actionable finding(s), were omitted from the live log.");
        }

        if (groups.Any(group => SclFindingAggregator.IsBlockingSeverity(group.Severity)))
            MarkDiagnosticAlert();
    }

    private static bool IsSmartDynamicCapabilityHint(SclWorkspaceFinding finding)
    {
        if (!finding.Severity.Equals("Warning", StringComparison.OrdinalIgnoreCase))
            return false;

        return finding.Code.Equals("SCL_REPORT_DATASET_UNASSIGNED", StringComparison.OrdinalIgnoreCase) ||
               finding.Code.Equals("SCL_REPORT_DATASET_UNRESOLVED", StringComparison.OrdinalIgnoreCase);
    }

    private static bool ShouldAllowDynamicReportingForScl(IReadOnlyCollection<SignalDefinition> signals)
    {
        return signals.Any(signal =>
            signal.CanPublishAsSignal &&
            (string.IsNullOrWhiteSpace(signal.DataSetReference) ||
             string.IsNullOrWhiteSpace(signal.ReportControlReference)));
    }

    private void TryAutoExpandCommandPanelOnce(Iec61850MonitorDevice? device)
    {
        if (device == null || CommandPanelExpander == null || device.CommandSignals.Count == 0)
            return;
        if (!_autoExpandedCommandDevices.Add(device.DeviceId))
            return;

        Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(() =>
        {
            if (ReferenceEquals(SelectedDevice, device) && CommandPanelExpander != null)
                CommandPanelExpander.IsExpanded = true;
        }));
    }

    private bool EnsureSclEndpointBinding'''
if "IsSmartDynamicCapabilityHint" not in cs:
    cs, count = log_method_pattern.subn(log_method_new, cs, count=1)
    if count != 1:
        raise SystemExit(f"LogSclFindings replacement: expected one method, replaced {count}")

cs = replace_once(
    cs,
    '''        device.IpAddress = wizard.RelayIpAddress;
        device.Port = wizard.MmsPort;
        device.Status = "SCL model ready";
        device.Detail = "Endpoint bound locally. Play will fast-connect from the SCL design model; Re-scan performs full comparison.";
        device.RefreshComputed();
''',
    '''        device.IpAddress = wizard.RelayIpAddress;
        device.Port = wizard.MmsPort;
        device.Status = "SCL model ready";
        device.Detail = device.AllowDynamicDataSetWrites
            ? "Endpoint bound locally. Saving the selected signals will connect and arm Smart Dynamic reporting with a safe free RCB before polling fallback."
            : "Endpoint bound locally. Play will fast-connect from the SCL design model; Re-scan performs full comparison.";
        device.RefreshComputed();
''',
    "endpoint binding detail")

cs = replace_once(
    cs,
    '''        device.RefreshCommandSignalProjection();
        RebuildControlFeedbackIndex(device);
        SetStatus($"{device.Name}: refreshed {candidates.Length} control value(s).");
''',
    '''        device.RefreshCommandSignalProjection();
        RebuildControlFeedbackIndex(device);
        TryAutoExpandCommandPanelOnce(device);
        SetStatus($"{device.Name}: refreshed {candidates.Length} control value(s).");
''',
    "command list ready expansion")

cs = replace_once(
    cs,
    '''                    AllowDynamicDataSetWrites = hasSclProvenance ? false : profile.AllowDynamicDataSetWrites,
''',
    '''                    AllowDynamicDataSetWrites = hasSclProvenance
                        ? ShouldAllowDynamicReportingForScl(cachedSignals)
                        : profile.AllowDynamicDataSetWrites,
''',
    "restored SCL dynamic reporting policy")

# P0 must remain present after all transformations.
required_p0_tokens = [
    "TryClaimControlConfirmation",
    "ControlInspectionBusy",
    "ControlCommandBusy",
    "ExecuteClaimedControlAsync"
]
for token in required_p0_tokens:
    if token not in cs:
        raise SystemExit(f"P0 regression guard: missing {token}")

write(cs_path, cs)


# ---------------------------------------------------------------------------
# Release alignment.
# ---------------------------------------------------------------------------
project_path = "ArIED61850Tester.csproj"
project = read(project_path)
project = project.replace("<Version>1.6.8</Version>", "<Version>1.6.9</Version>")
project = project.replace("<AssemblyVersion>1.6.8.0</AssemblyVersion>", "<AssemblyVersion>1.6.9.0</AssemblyVersion>")
project = project.replace("<FileVersion>1.6.8.0</FileVersion>", "<FileVersion>1.6.9.0</FileVersion>")
write(project_path, project)

workflow_path = ".github/workflows/build.yml"
workflow = read(workflow_path).replace("-Version 1.6.8", "-Version 1.6.9")
write(workflow_path, workflow)

publish_path = "scripts/publish-windows-portable.ps1"
publish = read(publish_path)
publish = publish.replace('[string]$Version = "1.6.8"', '[string]$Version = "1.6.9"')
publish = publish.replace("1.6.8 or v1.6.8", "1.6.9 or v1.6.9")
write(publish_path, publish)

Path("docs/SCL_SMART_DYNAMIC_REPORTING.md").write_text(
    """# SCL-assisted Smart Dynamic reporting\n\n"
    "Opening an SCL file is an offline operation. After the model is loaded, ArIED opens the signal-selection workflow immediately. Saving a valid live selection continues to endpoint binding, MMS association, and monitoring.\n\n"
    "When selected signals have complete static DataSet and ReportControl coverage, ArIED prefers that configuration. When coverage is missing or partial, ArIED prepares an association-scoped dynamic DataSet from the uncovered selected signals and asks the native engine to use a safe free RCB. MMS polling remains the final fallback.\n\n"
    "Unassigned or unresolved ReportControl DataSet references reported as warnings are retained in the typed SCL workspace but are not promoted into noisy live Diagnostics because they are capability hints handled by Smart Dynamic reporting. A positively resolved empty DataSet and other blocking SCL findings remain actionable diagnostics.\n\n"
    "The command panel expands automatically only once per IED, after the live control model has produced at least one proven executable command row.\n"
    """,
    encoding="utf-8")
