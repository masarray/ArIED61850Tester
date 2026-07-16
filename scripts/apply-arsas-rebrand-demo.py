from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return updated


# Main window branding, demo badge removal, and adapter rendering.
path = "MainWindow.xaml"
text = read(path)
text = text.replace('Title="ArIED 61850 — Smart IED Explorer &amp; Monitor"', 'Title="ARSAS - Smart IEC 61850 Communication Tester"')
text = text.replace('ToolTip="Open ArIED project"', 'ToolTip="Open ARSAS project"')
text = text.replace('ToolTip="Save ArIED project"', 'ToolTip="Save ARSAS project"')
text = text.replace('let ArIED discover the live IEC 61850 MMS model', 'let ARSAS discover the live IEC 61850 MMS model')
text = regex_once(
    text,
    r'\n\s*<Border Visibility="\{Binding DemoModeVisibility\}".*?</Border>\n\s*<Border Background="\{StaticResource PremiumSurface\}"',
    '\n                <Border Background="{StaticResource PremiumSurface}"',
    "remove demo badge",
)
text = replace_once(
    text,
    '''                                <ComboBox Grid.Column="2" ItemsSource="{Binding GooseAdapters}" SelectedItem="{Binding SelectedGooseAdapter, Mode=TwoWay}"
                                          DisplayMemberPath="DisplayText" Style="{StaticResource ModernComboBox}" MinHeight="34" Height="34" Padding="10,4"
                                          IsEnabled="{Binding CanRefreshGooseConfiguration}" ToolTip="{Binding SelectedGooseAdapterDetail}"/>''',
    '''                                <ComboBox Grid.Column="2" ItemsSource="{Binding GooseAdapters}" SelectedItem="{Binding SelectedGooseAdapter, Mode=TwoWay}"
                                          TextSearch.TextPath="DisplayText" Style="{StaticResource ModernComboBox}" MinHeight="34" Height="34" Padding="10,4"
                                          IsEnabled="{Binding CanRefreshGooseConfiguration}" ToolTip="{Binding SelectedGooseAdapterDetail}">
                                    <ComboBox.ItemTemplate>
                                        <DataTemplate>
                                            <TextBlock Text="{Binding DisplayText}" TextTrimming="CharacterEllipsis"/>
                                        </DataTemplate>
                                    </ComboBox.ItemTemplate>
                                </ComboBox>''',
    "adapter item template",
)
write(path, text)

# Application behavior, visible branding, demo action routing, and simulated commands.
path = "MainWindow.xaml.cs"
text = read(path)
text = text.replace('Ready. Add an IEC 61850 IED or open a saved ArIED project.', 'Ready. Add an IEC 61850 IED or open a saved ARSAS project.')
text = text.replace('ArIED 61850 started — Smart IED Explorer & Monitor.', 'ARSAS started — Smart IEC 61850 Communication Tester.')
text = text.replace('ArIED could not open this SCL file', 'ARSAS could not open this SCL file')
text = text.replace('ArIED will create', 'ARSAS will create').replace('ArIED will use', 'ARSAS will use')
text = text.replace('Save ArIED 61850 Project', 'Save ARSAS Project')
text = text.replace('Open ArIED 61850 Project', 'Open ARSAS Project')
text = text.replace('ArIED 61850 Project (*.aried.json)|*.aried.json', 'ARSAS Project (*.arsas.json)|*.arsas.json|Legacy ArIED Project (*.aried.json)|*.aried.json')
text = text.replace('ArIED-61850-Session.aried.json', 'ARSAS-Session.arsas.json')
text = text.replace('ArIED-61850-Events-', 'ARSAS-Events-')
text = replace_once(
    text,
    '''        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        SelectedDevice = device;

        if (!device.IsConnected)''',
    '''        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        SelectedDevice = device;
        if (device.IsDemo)
        {
            StartDemoDevice(device);
            return;
        }

        if (!device.IsConnected)''',
    "demo play routing",
)
text = replace_once(
    text,
    '''        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        SelectedDevice = device;

        if (device.IsMonitoring)
            await StopDeviceMonitorAsync(device);''',
    '''        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        SelectedDevice = device;
        if (device.IsDemo)
        {
            StopDemoDevice(device);
            return;
        }

        if (device.IsMonitoring)
            await StopDeviceMonitorAsync(device);''',
    "demo stop routing",
)
text = replace_once(
    text,
    '''    private async Task RefreshControlValuesAsync(Iec61850MonitorDevice device, bool force = false)
    {
        if (!device.IsConnected || device.CommandSignals.Count == 0)
            return;''',
    '''    private async Task RefreshControlValuesAsync(Iec61850MonitorDevice device, bool force = false)
    {
        if (device.IsDemo)
        {
            foreach (var signal in device.CommandSignals)
                signal.ControlLastResult = "Ready • live feedback available";
            return;
        }
        if (!device.IsConnected || device.CommandSignals.Count == 0)
            return;''',
    "demo control refresh",
)
text = replace_once(
    text,
    '''        try
        {
            if (!device.IsConnected)''',
    '''        try
        {
            if (device.IsDemo)
            {
                await ExecuteDemoControlAsync(device, signal, claim);
                return;
            }
            if (!device.IsConnected)''',
    "demo command execution",
)
text = replace_once(
    text,
    '''    private async void IedRemove_Click(object sender, RoutedEventArgs e)
    {
        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        SaveSignalSelectionMemory(device);''',
    '''    private async void IedRemove_Click(object sender, RoutedEventArgs e)
    {
        if (!TryGetDeviceFromButton(sender, out var device) || device.IsBusy) return;
        if (device.IsDemo)
        {
            RemoveDemoDevice(device);
            return;
        }
        SaveSignalSelectionMemory(device);''',
    "demo remove routing",
)
write(path, text)

# Demo identity, short IED names, realistic acquisition labels, and no visible demo wording.
path = "MainWindow.Demo.cs"
text = read(path)
text = text.replace('public Visibility DemoModeVisibility => _isDemoMode ? Visibility.Visible : Visibility.Collapsed;', 'public Visibility DemoModeVisibility => Visibility.Collapsed;')
text = text.replace('public string DemoModeText => $"DEMO MODE • {DemoShortcutText}";', 'public string DemoModeText => string.Empty;')
text = text.replace('Disconnect every live IED and stop GOOSE capture before entering Demo Mode.', 'Disconnect every active IED and stop GOOSE capture before loading the communication workspace.')
text = text.replace('"Demo Mode",', '"ARSAS Workspace",')
text = text.replace('Demo Mode replaces the current offline workspace with synthetic substation data. Save the current project first if it must be retained.', 'The communication workspace replaces the current offline workspace. Save the current project first if it must be retained.')
text = text.replace('"Load Demo Workspace",', '"Load Communication Workspace",')
text = text.replace('Title = "ArIED 61850 — Synthetic Substation Demo";', 'Title = "ARSAS - Smart IEC 61850 Communication Tester";')
text = text.replace('Title = "ArIED 61850 — Smart IED Explorer & Monitor";', 'Title = "ARSAS - Smart IEC 61850 Communication Tester";')
text = text.replace('SetStatus($"DEMO MODE active • 10 synthetic IEDs • {GlobalPoints.Count:N0} live values • {GooseStreams.Count:N0} GOOSE publishers • press {DemoShortcutText} to exit.");', 'SetStatus($"Communication workspace ready • 10 connected IEDs • {GlobalPoints.Count:N0} live values • {GooseStreams.Count:N0} GOOSE publishers.");')
text = text.replace('AddLog("INFO", "Demo", "Synthetic substation demo closed. No network sessions were created.");', 'AddLog("INFO", "System", "Communication workspace cleared.");')
text = text.replace('SetStatus($"Demo workspace cleared. Press {DemoShortcutText} to load it again.");', 'SetStatus("Ready. Add an IEC 61850 IED or open a saved ARSAS project.");')
name_map = {
    'BCU_INCOMER_150KV': 'E02BCU1',
    'BCU_TRAFO_BAY_TR1': 'E03BCU2',
    'PROT_OCR_INCOMER_20KV': 'E05OCR1',
    'PROT_OCR_FEEDER_F01': 'E06OCR2',
    'PROT_LINE_DIFF_L01': 'E02LDIF1',
    'PROT_DISTANCE_L02': 'E03DIST1',
    'PROT_TRAFO_DIFF_TR1': 'E03TDIF1',
    'PROT_BUSBAR_DIFF_BB1': 'E04BDIF1',
    'PROT_CAPBANK_CB1': 'E05CAP1',
    'BCU_BUS_COUPLER_150KV': 'E06BCU3',
}
for old, new in name_map.items():
    text = text.replace(old, new)
text = text.replace('3 LD •', '4 LD •').replace('2 LD •', '4 LD •')
text = replace_once(
    text,
    '''        for (var deviceIndex = 0; deviceIndex < deviceSpecs.Length; deviceIndex++)
        {''',
    '''        var reportInstances = new[]
        {
            "A_BRCB01", "A_BRCB101", "A_BRCB201", "A_BRCB301", "A_BRCB401",
            "A_BRCB501", "A_BRCB601", "A_BRCB701", "A_BRCB801", "A_BRCB901"
        };

        for (var deviceIndex = 0; deviceIndex < deviceSpecs.Length; deviceIndex++)
        {''',
    "demo report instances",
)
text = text.replace('IdentitySource = $"DEMO • live MMS discovery • {spec.Description}"', 'IdentitySource = $"Live MMS discovery • SIPROTEC-class {spec.Description}"')
text = text.replace('Status = "Monitoring • BRCB active"', 'Status = "Monitoring • BRCB active"')
text = text.replace('Detail = $"Synthetic {spec.Description} session. Buffered reports, MMS validation reads and GOOSE bindings are generated locally; no packets are transmitted."', 'Detail = $"Active {spec.Description} communication session with report acquisition, MMS verification and GOOSE model binding."')
text = regex_once(
    text,
    r'AcquisitionMode = deviceIndex % 3 == 0\s*\? "Buffered Report • dchg/qchg/dupd"\s*: deviceIndex % 3 == 1\s*\? "Unbuffered Report • dchg \+ integrity"\s*: "Static DataSet report • MMS verification",',
    'AcquisitionMode = $"Dynamic: {reportInstances[deviceIndex]}",',
    "demo acquisition mode",
)
text = text.replace('AddDemoPoint(device, seed, deviceIndex);', 'AddDemoPoint(device, seed, deviceIndex, reportInstances[deviceIndex]);')
text = text.replace('            device.RecountSelectedSignals();', '            AddDemoCircuitBreakerControl(device);\n            device.RecountSelectedSignals();')
write(path, text)

# Realistic demo telegrams, quality, acquisition, and trip-phase events.
path = "MainWindow.DemoSignals.cs"
text = read(path)
text = text.replace('private void AddDemoPoint(Iec61850MonitorDevice device, DemoSignalSeed seed, int deviceIndex)', 'private void AddDemoPoint(Iec61850MonitorDevice device, DemoSignalSeed seed, int deviceIndex, string reportInstance)')
text = text.replace('var reference = $"{device.Name}LD0/{seed.Path}";', 'var reference = $"{device.Name}{ResolveDemoLogicalDevice(seed)}/{seed.Path}";')
text = text.replace('var dataSet = $"{device.Name}LD0/LLN0$DataSet$dsOperational";', 'var dataSet = $"{device.Name}DR/LLN0$DataSet$A_DS01";')
text = text.replace('var rcb = $"{device.Name}LD0/LLN0$BR$brcbOperational01";', 'var rcb = $"{device.Name}DR/LLN0$BR${reportInstance}";')
text = text.replace('Source = "DEMO • live discovery"', 'Source = "Live MMS discovery"')
text = text.replace('ReportCoverage = deviceIndex % 2 == 0 ? "Buffered Report • dchg/qchg" : "Unbuffered Report • dchg/dupd"', 'ReportCoverage = $"Dynamic: {reportInstance}"')
text = text.replace('Quality = "Good • validity=good"', 'Quality = "Good"')
text = text.replace('SourceMode = deviceIndex % 2 == 0 ? "Buffered Report • dchg" : "Unbuffered Report • dupd"', 'SourceMode = $"Dynamic: {reportInstance}"')
text = text.replace('SourceMode = "Buffered Report • dchg",', 'SourceMode = state.Device.AcquisitionMode,')
text = text.replace('Quality = "Good • validity=good",', 'Quality = "Good",')
text = text.replace('Boolean("Overcurrent stage 1 pickup", "PTOC1.Str.general", false, true),\n                Boolean("Overcurrent stage 2 trip", "PTOC2.Op.general", false, true),\n                Boolean("Earth-fault pickup", "PTOC3.Str.general", false, true),\n                Boolean("Master trip", "PTRC1.Tr.general", false, true)', 'Boolean("Overcurrent trip phase A", "PTOC1.Op.phsA", false, true),\n                Boolean("Overcurrent trip phase B", "PTOC1.Op.phsB", false, true),\n                Boolean("Earth-fault trip", "PTOC2.Op.general", false, true),\n                Boolean("Master trip", "PTRC1.Op.general", false, true)')
text = text.replace('Boolean("Line differential pickup", "PDIF1.Str.general", false, true),\n                Boolean("Line differential trip", "PDIF1.Op.general", false, true),\n                Boolean("Teleprotection receive", "PSCH1.Op.general", false, true),', 'Boolean("Line differential trip phase A", "PDIF1.Op.phsA", false, true),\n                Boolean("Line differential trip phase B", "PDIF1.Op.phsB", false, true),\n                Boolean("Line differential trip", "PDIF1.Op.general", false, true),')
text = text.replace('Boolean("Transformer differential pickup", "PDIF1.Str.general", false, true),\n                Boolean("Transformer differential trip", "PDIF1.Op.general", false, true),\n                Boolean("Inrush restraint", "PHAR1.Str.general", false, true),', 'Boolean("Transformer differential trip phase A", "PDIF1.Op.phsA", false, true),\n                Boolean("Transformer differential trip phase B", "PDIF1.Op.phsB", false, true),\n                Boolean("Transformer differential trip", "PDIF1.Op.general", false, true),')
write(path, text)

# Demo runtime quality and acquisition labels.
path = "MainWindow.DemoProcessRuntime.cs"
text = read(path)
text = text.replace('"Good • validity=good"', '"Good"')
text = text.replace('state.Point.SourceMode = _demoTick % 5 == 0 ? "MMS validation read" : "Buffered Report • dupd";', 'state.Point.SourceMode = _demoTick % 5 == 0 ? "MMS validation read" : state.Device.AcquisitionMode;')
text = text.replace('state.Point.SourceMode = "Buffered Report • dchg";', 'state.Point.SourceMode = state.Device.AcquisitionMode;')
text = text.replace('SourceMode = "Buffered Report • dchg",', 'SourceMode = state.Device.AcquisitionMode,')
write(path, text)

# GOOSE demo identities, adapter name, and non-LD0 references.
path = "MainWindow.DemoGooseData.cs"
text = read(path)
for old, new in name_map.items():
    text = text.replace(old, new)
text = text.replace('Name = "demo://station-bus"', 'Name = "\\\\Device\\NPF_{A1B2C3D4-E5F6-47A8-9012-3456789ABCDE}"')
text = text.replace('FriendlyName = "Station Bus VLAN 100 (Synthetic)"', 'FriendlyName = "Intel(R) Ethernet Connection I219-LM - Station Bus"')
text = text.replace('Description = "ArIED built-in demonstration adapter"', 'Description = "Intel(R) Ethernet Connection (7) I219-LM"')
text = text.replace('GooseBindingText = "DEMO model binding • 6 publishers • ordered DataSet leaves resolved from synthetic IED models";', 'GooseBindingText = "6 publishers • ordered DataSet leaves resolved from SCL and live MMS models";')
text = text.replace('GooseStatusText = "DEMO • synthetic read-only GOOSE capture is running; no Ethernet frames are transmitted or received.";', 'GooseStatusText = "Receiving GOOSE • 6 publishers • sequence and TAL supervision active.";')
text = text.replace('new() { Time = now.AddMinutes(-8), Level = "INFO", Source = "Demo", Message = "Synthetic substation workspace initialized. Network transport is disabled." },', 'new() { Time = now.AddMinutes(-8), Level = "INFO", Source = "System", Message = "ARSAS communication workspace initialized." },')
text = text.replace('10 independent IEC 61850 associations established on TCP/102 (synthetic).', '10 independent IEC 61850 associations established on TCP/102.')
text = text.replace('PROT_TRAFO_DIFF_TR1', 'E03TDIF1')
write(path, text)

path = "MainWindow.DemoGooseSnapshot.cs"
text = read(path)
text = text.replace('        var leaves = state.Leaves.Select((leaf, index) =>', '        var logicalDevice = state.Spec.IedName.Contains("BCU", StringComparison.OrdinalIgnoreCase) ? "CTRL" : "PROT";\n        var leaves = state.Leaves.Select((leaf, index) =>')
text = text.replace('$"{state.Spec.IedName}LD0/{leaf.Path}"', '$"{state.Spec.IedName}{logicalDevice}/{leaf.Path}"')
text = text.replace('$"{state.Spec.IedName}LD0/LLN0$GO${state.Spec.ControlBlock}"', '$"{state.Spec.IedName}{logicalDevice}/LLN0$GO${state.Spec.ControlBlock}"')
text = text.replace('$"{state.Spec.IedName}LD0/LLN0$DataSet${state.Spec.DataSet}"', '$"{state.Spec.IedName}{logicalDevice}/LLN0$DataSet${state.Spec.DataSet}"')
text = text.replace('"DEMO model"', '"SCL / live model"')
write(path, text)

# Demo card action availability.
path = "Models/MonitorModels.cs"
text = read(path)
text = text.replace('public bool IsActionEnabled => !IsBusy && !IsDemo;', 'public bool IsActionEnabled => !IsBusy;')
text = text.replace('public bool CanStartMonitor => IsConnected && SelectedLiveSignalCount > 0 && !IsBusy && !IsDemo;', 'public bool CanStartMonitor => IsConnected && SelectedLiveSignalCount > 0 && !IsBusy;')
text = text.replace('public bool CanStartOrStopMonitor => !IsBusy && !IsDemo && (IsMonitoring || SelectedLiveSignalCount > 0);', 'public bool CanStartOrStopMonitor => !IsBusy && (IsMonitoring || SelectedLiveSignalCount > 0);')
text = text.replace('public bool CanPlayAction => !IsBusy && !IsDemo && (!IsConnected || (!IsMonitoring && SelectedLiveSignalCount > 0));', 'public bool CanPlayAction => !IsBusy && (!IsConnected || (!IsMonitoring && SelectedLiveSignalCount > 0));')
text = text.replace('public bool CanStopAction => !IsBusy && !IsDemo && (IsConnected || IsMonitoring);', 'public bool CanStopAction => !IsBusy && (IsConnected || IsMonitoring);')
text = text.replace('public string ProjectName { get; set; } = "ArIED 61850 Session";', 'public string ProjectName { get; set; } = "ARSAS Session";')
write(path, text)

# Adapter fail-safe rendering.
path = "Models/GooseSubscriberModels.cs"
text = read(path)
text = replace_once(
    text,
    '''    public string DetailText => string.Join(" • ", new[] { FriendlyName, Description, MacAddress, Name }
        .Where(value => !string.IsNullOrWhiteSpace(value))
        .Distinct(StringComparer.OrdinalIgnoreCase));''',
    '''    public string DetailText => string.Join(" • ", new[] { FriendlyName, Description, MacAddress, Name }
        .Where(value => !string.IsNullOrWhiteSpace(value))
        .Distinct(StringComparer.OrdinalIgnoreCase));
    public override string ToString() => DisplayText;''',
    "adapter tostring",
)
write(path, text)

# Product and executable branding.
path = "ArIED61850Tester.csproj"
text = read(path)
text = text.replace('<AssemblyName>ArIED61850</AssemblyName>', '<AssemblyName>ARSAS</AssemblyName>')
text = text.replace('<Product>ArIED 61850</Product>', '<Product>ARSAS</Product>')
text = text.replace('<AssemblyTitle>ArIED 61850 — IEC 61850 Engineering Workstation</AssemblyTitle>', '<AssemblyTitle>ARSAS - Smart IEC 61850 Communication Tester</AssemblyTitle>')
text = text.replace('Windows IEC 61850 engineering workstation', 'Smart Windows IEC 61850 communication tester')
text = text.replace('ArIED 61850 is compiling', 'ARSAS is compiling')
text = text.replace('ArIED 61850 GOOSE Subscriber is compiling', 'ARSAS GOOSE Subscriber is compiling')
write(path, text)

path = "scripts/publish-windows-portable.ps1"
text = read(path)
text = text.replace('ArIED61850-$normalizedVersion-$Runtime', 'ARSAS-$normalizedVersion-$Runtime')
text = text.replace('ArIED61850-$normalizedVersion-$Runtime-portable.zip', 'ARSAS-$normalizedVersion-$Runtime-portable.zip')
text = text.replace('Restoring ArIED 61850', 'Restoring ARSAS')
text = text.replace('ArIED61850.exe', 'ARSAS.exe')
text = text.replace('Put the ArIED source folder', 'Put the ARSAS source folder')
write(path, text)

path = "scripts/build-windows-installer.ps1"
text = read(path)
text = text.replace('dist\\ArIED61850-$normalizedVersion-$Runtime', 'dist\\ARSAS-$normalizedVersion-$Runtime')
text = text.replace('"ArIED61850.exe"', '"ARSAS.exe"')
text = text.replace('ArIED61850-$normalizedVersion-$Runtime-setup', 'ARSAS-$normalizedVersion-$Runtime-setup')
write(path, text)

path = "installer/ArIED61850.iss"
text = read(path)
text = text.replace('; ArIED 61850 Windows installer', '; ARSAS Windows installer')
text = text.replace('"ArIED61850-setup"', '"ARSAS-setup"')
text = text.replace('#define AppName "ArIED 61850"', '#define AppName "ARSAS - Smart IEC 61850 Communication Tester"')
text = text.replace('#define AppExeName "ArIED61850.exe"', '#define AppExeName "ARSAS.exe"')
text = text.replace('DefaultDirName={autopf}\\ArIED 61850', 'DefaultDirName={autopf}\\ARSAS')
text = text.replace('DefaultGroupName=ArIED 61850', 'DefaultGroupName=ARSAS')
text = text.replace('Name: "{autoprograms}\\ArIED 61850"', 'Name: "{autoprograms}\\ARSAS"')
text = text.replace('Name: "{autodesktop}\\ArIED 61850"', 'Name: "{autodesktop}\\ARSAS"')
text = text.replace('Description: "Launch ArIED 61850"', 'Description: "Launch ARSAS"')
text = text.replace('ArIED 61850 is installed', 'ARSAS is installed')
write(path, text)

# CI display/artifact branding while retaining repository folder paths.
path = ".github/workflows/build.yml"
text = read(path)
text = text.replace('name: Build ArIED 61850', 'name: Build ARSAS')
text = text.replace('name: ArIED61850-source-snapshot', 'name: ARSAS-source-snapshot')
text = text.replace('name: ArIED61850-win-x64', 'name: ARSAS-win-x64')
write(path, text)

# README and landing-page product identity; repository URLs remain unchanged.
for path in ["README.md", "landing/index.html", "landing/features.html", "landing/control.html", "landing/architecture.html", "landing/site.webmanifest"]:
    text = read(path)
    text = text.replace('ArIED 61850', 'ARSAS')
    text = re.sub(r'\bArIED\b', 'ARSAS', text)
    text = text.replace('ArIED61850"', 'ARSAS"')
    write(path, text)

# Additional user-facing report and command-origin branding.
for path in ["Services/DiagnosticReportBuilder.cs", "Models/ControlModels.cs"]:
    text = read(path)
    text = text.replace('ArIED 61850', 'ARSAS').replace('ArIED61850', 'ARSAS')
    write(path, text)

print("Applied ARSAS rebrand, realistic demo communication data, interactive demo IED controls, and adapter rendering fixes.")
