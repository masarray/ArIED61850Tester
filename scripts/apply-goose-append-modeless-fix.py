from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# 1) Append-only timeline and concise current values.
path = Path("MainWindow.GooseTimeline.cs")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''            GooseEvents.Insert(0, eventRow);
            while (GooseEvents.Count > MaxGooseTimelineEvents)
                GooseEvents.RemoveAt(GooseEvents.Count - 1);

            SelectedGooseEvent ??= eventRow;''',
    '''            // Append in capture order. Adding at the tail avoids shifting every realized
            // DataGrid row on each state change and is substantially lighter during long captures.
            GooseEvents.Add(eventRow);
            while (GooseEvents.Count > MaxGooseTimelineEvents)
                GooseEvents.RemoveAt(0);

            SelectedGooseEvent ??= eventRow;''',
    "append-only GOOSE timeline")
old_summary = '''        var changed = stream.Leaves
            .Where(leaf => leaf.IsChanged)
            .Take(2)
            .Select(leaf =>
            {
                var previous = string.IsNullOrWhiteSpace(leaf.PreviousValue)
                    ? "-"
                    : ShortenGooseText(GooseEngineeringValueFormatter.Format(leaf.PreviousValue), 30);
                var current = GooseEngineeringValueFormatter.Format(leaf.Value);
                return $"{leaf.SignalName}: {previous} → {ShortenGooseText(current, 36)}";
            })
            .ToArray();
        if (changed.Length > 0)
        {
            var suffix = stream.ChangedValueCount > changed.Length
                ? $" • +{stream.ChangedValueCount - changed.Length:N0} more"
                : string.Empty;
            return string.Join(" • ", changed) + suffix;
        }'''
new_summary = '''        var changed = stream.Leaves
            .Where(leaf => leaf.IsChanged)
            .Take(2)
            .Select(leaf =>
            {
                var current = ShortenGooseText(GooseEngineeringValueFormatter.Format(leaf.Value), 30);
                return IsGenericGooseLeafName(leaf.SignalName)
                    ? current
                    : $"{ShortenGooseText(leaf.SignalName, 22)}: {current}";
            })
            .ToArray();
        if (changed.Length > 0)
        {
            var suffix = stream.ChangedValueCount > changed.Length
                ? $" • +{stream.ChangedValueCount - changed.Length:N0}"
                : string.Empty;
            return string.Join(" • ", changed) + suffix;
        }'''
text = replace_once(text, old_summary, new_summary, "concise GOOSE values")
text = replace_once(
    text,
    '''    private static string FriendlySequenceStatus(string value)
    {''',
    '''    private static bool IsGenericGooseLeafName(string? value)
    {
        var text = value?.Trim() ?? string.Empty;
        return string.IsNullOrWhiteSpace(text) ||
               text.StartsWith("Leaf ", StringComparison.OrdinalIgnoreCase);
    }

    private static string FriendlySequenceStatus(string value)
    {''',
    "generic leaf helper")
path.write_text(text, encoding="utf-8")


# 2) Keep the latest raw frame per stream and automatically rebind current rows when
# an IED/SCL model becomes available, even while capture is running.
path = Path("MainWindow.GooseSubscriber.cs")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    private readonly ConcurrentDictionary<string, GooseSubscriberFrameSnapshot> _pendingGooseFrames = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, GooseStreamRow> _gooseStreamIndex = new(StringComparer.OrdinalIgnoreCase);''',
    '''    private readonly ConcurrentDictionary<string, GooseSubscriberFrameSnapshot> _pendingGooseFrames = new(StringComparer.OrdinalIgnoreCase);
    private readonly ConcurrentDictionary<string, GooseSubscriberFrameSnapshot> _latestGooseFrames = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, GooseStreamRow> _gooseStreamIndex = new(StringComparer.OrdinalIgnoreCase);''',
    "latest GOOSE frame cache")
text = replace_once(
    text,
    '''    private bool _gooseWorkspaceActivationScheduled;
''',
    '''    private bool _gooseWorkspaceActivationScheduled;
    private bool _gooseBindingRefreshScheduled;
''',
    "binding refresh state")
text = replace_once(
    text,
    '''        _pendingGooseFrames.Clear();
        _gooseStreamIndex.Clear();''',
    '''        _pendingGooseFrames.Clear();
        _latestGooseFrames.Clear();
        _gooseStreamIndex.Clear();''',
    "clear latest frames")
text = replace_once(
    text,
    '''    private void RefreshGooseBindingPreview()
    {
        if (IsGooseCapturing)
            return;

        try
        {
            _gooseBindingCatalog = BuildGooseBindingCatalog();
            GooseBindingText = _gooseBindingCatalog.Summary;
        }
        catch (Exception ex)
        {''',
    '''    private void RefreshGooseBindingPreview()
    {
        try
        {
            _gooseBindingCatalog = BuildGooseBindingCatalog();
            GooseBindingText = _gooseBindingCatalog.Summary;
            RebindGooseRowsFromLatestFrames();
        }
        catch (Exception ex)
        {''',
    "refresh binding while capture runs")
text = replace_once(
    text,
    '''    private void ApplyGooseWorkspaceFallback(string context, Exception exception)
    {''',
    '''    private void ScheduleGooseBindingRefreshFromWorkspace()
    {
        if ((!_goosePresentationInstalled && !IsGooseCapturing) ||
            _gooseBindingRefreshScheduled || Dispatcher.HasShutdownStarted)
        {
            return;
        }

        _gooseBindingRefreshScheduled = true;
        Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(() =>
        {
            _gooseBindingRefreshScheduled = false;
            RefreshGooseBindingPreview();
        }));
    }

    private void RebindGooseRowsFromLatestFrames()
    {
        foreach (var captured in _latestGooseFrames.Values.Take(256))
        {
            if (!_gooseStreamIndex.TryGetValue(captured.StreamKey, out var row))
                continue;

            row.Apply(BuildGooseStreamSnapshot(captured, _gooseBindingCatalog));
        }

        Raise(nameof(GooseSelectedStreamText));
        Raise(nameof(GooseNoLeafValuesVisibility));
        Raise(nameof(GooseSelectedLeafCountText));
    }

    private void ApplyGooseWorkspaceFallback(string context, Exception exception)
    {''',
    "automatic GOOSE rebinding")
text = replace_once(
    text,
    '''    private void GooseSubscriberRuntime_FrameReceived(GooseSubscriberFrameSnapshot snapshot)
        => _pendingGooseFrames[snapshot.StreamKey] = snapshot;''',
    '''    private void GooseSubscriberRuntime_FrameReceived(GooseSubscriberFrameSnapshot snapshot)
    {
        _latestGooseFrames[snapshot.StreamKey] = snapshot;
        _pendingGooseFrames[snapshot.StreamKey] = snapshot;
    }''',
    "cache latest GOOSE frames")
path.write_text(text, encoding="utf-8")


# 3) Make Signal Selection owned/modeless: always above the main window, but the main
# workspace and other IED cards remain clickable during discovery and mapping.
path = Path("SignalSelectionWizardWindow.xaml.cs")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    public event PropertyChangedEventHandler? PropertyChanged;

    public ICollectionView SignalsView { get; }''',
    '''    public event PropertyChangedEventHandler? PropertyChanged;

    public bool Accepted => _accepted;
    public ICollectionView SignalsView { get; }''',
    "wizard accepted property")
text = replace_once(
    text,
    '''    private void Save_Click(object sender, RoutedEventArgs e)
    {
        _accepted = true;
        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        RestoreOriginalSelection();
        DialogResult = false;
    }''',
    '''    private void Save_Click(object sender, RoutedEventArgs e)
    {
        _accepted = true;
        Close();
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
        => Close();''',
    "modeless wizard close semantics")
path.write_text(text, encoding="utf-8")

path = Path("MainWindow.xaml.cs")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''        device.Signals.AddRange(signals);
        device.RecountSelectedSignals();
        device.RefreshComputed();
    }

    private static string BuildSclWorkspaceSummary''',
    '''        device.Signals.AddRange(signals);
        device.RecountSelectedSignals();
        device.RefreshComputed();
        ScheduleGooseBindingRefreshFromWorkspace();
    }

    private static string BuildSclWorkspaceSummary''',
    "SCL triggers GOOSE rebinding")
text = replace_once(
    text,
    '''            device.Signals.AddRange(signals);
            device.HasDiscoveryCache = signals.Count > 0;
            ApplySclLiveComparison(device, signals);

            try''',
    '''            device.Signals.AddRange(signals);
            device.HasDiscoveryCache = signals.Count > 0;
            ApplySclLiveComparison(device, signals);
            ScheduleGooseBindingRefreshFromWorkspace();

            try''',
    "live discovery triggers GOOSE rebinding")
text = replace_once(
    text,
    '''            // Let the card-local bar visibly settle at 100%, then release the card
            // before opening a modal wizard or starting live monitoring.
            await WaitForDiscoveryProgressAnimationAsync(device, TimeSpan.FromMilliseconds(1800));''',
    '''            // Let the card-local bar settle briefly without holding the discovery workflow
            // in a long cosmetic delay. Signal mapping is modeless, so the workspace stays usable.
            await WaitForDiscoveryProgressAnimationAsync(device, TimeSpan.FromMilliseconds(650));''',
    "lighter discovery completion delay")
text = replace_once(
    text,
    '''        var wizard = new SignalSelectionWizardWindow(
            device,
            restoredSelectionCount < 0 ? device.SelectedSignalCount : restoredSelectionCount)
        {
            Owner = this
        };

        _signalSelectionWizardOpen = true;
        try
        {
            if (wizard.ShowDialog() != true)
            {
                device.RefreshComputed();
                RaiseWorkspaceCounts();
                SetStatus($"{device.Name}: signal selection unchanged.");
                return false;
            }
''',
    '''        var wizard = new SignalSelectionWizardWindow(
            device,
            restoredSelectionCount < 0 ? device.SelectedSignalCount : restoredSelectionCount)
        {
            Owner = this,
            ShowInTaskbar = false,
            WindowStartupLocation = WindowStartupLocation.CenterOwner
        };

        _signalSelectionWizardOpen = true;
        try
        {
            var completion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            void WizardClosed(object? sender, EventArgs args)
            {
                wizard.Closed -= WizardClosed;
                completion.TrySetResult(wizard.Accepted);
            }

            wizard.Closed += WizardClosed;
            wizard.Show();
            var accepted = await completion.Task;
            if (!accepted)
            {
                device.RefreshComputed();
                RaiseWorkspaceCounts();
                SetStatus($"{device.Name}: signal selection unchanged.");
                return false;
            }
''',
    "owned modeless signal selection")
path.write_text(text, encoding="utf-8")


# 4) Remove visual noise from the command header.
path = Path("MainWindow.xaml")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''                                        <TextBlock Text="IED Command Panel" FontSize="13.6" FontWeight="SemiBold" Foreground="{StaticResource Ink}" VerticalAlignment="Center"/>
                                        <Border Background="#EAF2FF" BorderBrush="#C7D8F2" BorderThickness="1" CornerRadius="10" Padding="7,2" Margin="9,0,0,0">
                                            <TextBlock Text="{Binding SelectedDevice.CommandSignals.Count, StringFormat={}{0} controls}" FontSize="10.8" FontWeight="SemiBold" Foreground="#45648E"/>
                                        </Border>''',
    '''                                        <TextBlock Text="IED Command Panel" FontSize="13.6" FontWeight="SemiBold" Foreground="{StaticResource Ink}" VerticalAlignment="Center"/>''',
    "command count visual noise")
path.write_text(text, encoding="utf-8")


# 5) Fix ComboBox hit-surface hover and simplify event value column.
path = Path("App.xaml")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''                            <ToggleButton Background="Transparent" BorderThickness="0" Focusable="False" Cursor="Hand"
                                          IsChecked="{Binding IsDropDownOpen, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}"/>''',
    '''                            <ToggleButton Background="Transparent" BorderThickness="0" Focusable="False" Cursor="Hand"
                                          IsChecked="{Binding IsDropDownOpen, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}">
                                <ToggleButton.Template>
                                    <ControlTemplate TargetType="ToggleButton">
                                        <Border Background="Transparent"/>
                                    </ControlTemplate>
                                </ToggleButton.Template>
                            </ToggleButton>''',
    "transparent ComboBox hit surface")
path.write_text(text, encoding="utf-8")

path = Path("Views/GooseSubscriberLiteView.xaml")
text = path.read_text(encoding="utf-8")
old_combo = '''                    <ComboBox Grid.Column="2" ItemsSource="{Binding GooseAdapters}"
                              SelectedItem="{Binding SelectedGooseAdapter, Mode=TwoWay}"
                              Style="{StaticResource ModernComboBox}" Height="34" Padding="10,4"
                              IsHitTestVisible="{Binding CanRefreshGooseConfiguration}"
                              Focusable="{Binding CanRefreshGooseConfiguration}"
                              ToolTip="{Binding SelectedGooseAdapterDetail}">
                        <ComboBox.ItemTemplate>
                            <DataTemplate>
                                <TextBlock Text="{Binding DisplayText}" TextTrimming="CharacterEllipsis"/>
                            </DataTemplate>
                        </ComboBox.ItemTemplate>
                    </ComboBox>'''
new_combo = '''                    <ComboBox Grid.Column="2" ItemsSource="{Binding GooseAdapters}"
                              SelectedItem="{Binding SelectedGooseAdapter, Mode=TwoWay}"
                              DisplayMemberPath="DisplayText" TextSearch.TextPath="DisplayText"
                              Style="{StaticResource ModernComboBox}" Height="34" Padding="10,4"
                              IsHitTestVisible="{Binding CanRefreshGooseConfiguration}"
                              Focusable="{Binding CanRefreshGooseConfiguration}"
                              ToolTip="{Binding SelectedGooseAdapterDetail}"/>'''
text = replace_once(text, old_combo, new_combo, "GOOSE adapter display member")
text = replace_once(
    text,
    '<DataGridTextColumn Header="Changed values" Binding="{Binding Summary}" Width="*" MinWidth="150"/>',
    '<DataGridTextColumn Header="Values" Binding="{Binding Summary}" Width="*" MinWidth="150"/>',
    "GOOSE values column")
path.write_text(text, encoding="utf-8")


# 6) Add source-level regressions for the exact requested behavior.
path = Path(".github/workflows/build.yml")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''          $gooseRuntime = Get-Content .\\ArIED61850Tester\\Services\\GooseSubscriberRuntime.cs -Raw
          $gooseModels = Get-Content .\\ArIED61850Tester\\Models\\GooseSubscriberModels.cs -Raw
''',
    '''          $gooseRuntime = Get-Content .\\ArIED61850Tester\\Services\\GooseSubscriberRuntime.cs -Raw
          $gooseModels = Get-Content .\\ArIED61850Tester\\Models\\GooseSubscriberModels.cs -Raw
          $gooseTimeline = Get-Content .\\ArIED61850Tester\\MainWindow.GooseTimeline.cs -Raw
          $gooseLite = Get-Content .\\ArIED61850Tester\\Views\\GooseSubscriberLiteView.xaml -Raw
          $signalWizard = Get-Content .\\ArIED61850Tester\\SignalSelectionWizardWindow.xaml.cs -Raw
''',
    "CI file inputs")
text = replace_once(
    text,
    '''               $gooseModels -notmatch 'FlagsText' -or
               $project -notmatch 'ArIec61850NpcapProject' -or''',
    '''               $gooseModels -notmatch 'FlagsText' -or
               $gooseTimeline -notmatch 'GooseEvents.Add\\(eventRow\\)' -or
               $gooseTimeline -match 'GooseEvents.Insert\\(0, eventRow\\)' -or
               $gooseTimeline -notmatch 'IsGenericGooseLeafName' -or
               $gooseLite -notmatch 'Header="Values"' -or
               $gooseLite -match 'Header="Changed values"' -or
               $gooseLite -notmatch 'DisplayMemberPath="DisplayText"' -or
               $code -notmatch 'wizard.Show\\(\\)' -or
               $code -match 'wizard.ShowDialog\\(\\)' -or
               $signalWizard -match 'DialogResult\\s*=' -or
               $main -match 'StringFormat=\\{\\}\\{0\\} controls' -or
               $project -notmatch 'ArIec61850NpcapProject' -or''',
    "CI behavior invariants")
path.write_text(text, encoding="utf-8")

print("Applied append-only GOOSE timeline, live model rebinding, modeless signal selection, dropdown fix, and command-header cleanup.")
