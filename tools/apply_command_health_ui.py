from pathlib import Path
import re

def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,s): Path(p).write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
def one(s,a,b,n):
    c=s.count(a)
    if c!=1: raise RuntimeError(f'{n}: {c}')
    return s.replace(a,b,1)
def sub(s,p,r,n):
    s,c=re.subn(p,r,s,count=1,flags=re.S)
    if c!=1: raise RuntimeError(f'{n}: {c}')
    return s

# Stop the implicit DataGridRow style from binding MonitorPoint-only state on SignalDefinition rows.
p='App.xaml'; s=read(p)
s=sub(s,r'\s*<!-- Runtime live-value edge highlight\..*?</DataTrigger>', '', 'global row flash binding')
write(p,s)

p='MainWindow.CommandPanelUx.cs'; s=read(p)
s=one(s,'using ArIED61850Tester.Models;\n','using ArIED61850Tester.Models;\nusing ArIED61850Tester.Services;\n','formatter import')
s=one(s,'''            var supportsOperate = values.ElementAtOrDefault(3) is true;
            return (liveArmed || testMode) && supportsOperate && !busy;
''','''            var supportsOperate = values.ElementAtOrDefault(3) is true;
            var current = values.ElementAtOrDefault(4)?.ToString() ?? string.Empty;
            var command = parameter?.ToString() ?? string.Empty;
            return (liveArmed || testMode) && supportsOperate && !busy && !AlreadyActive(command, current);
        }

        private static bool AlreadyActive(string command, string current)
        {
            if (string.IsNullOrWhiteSpace(command) || string.IsNullOrWhiteSpace(current) || current.Trim() == "-") return false;
            if (Iec61850ValueFormatter.TryNormalizeDbpos(command, out var requested) &&
                Iec61850ValueFormatter.TryNormalizeDbpos(current, out var actual)) return requested == actual;
            if (bool.TryParse(command, out var requestedBool) && bool.TryParse(current, out var actualBool)) return requestedBool == actualBool;
            return command.Trim().Equals(current.Trim(), StringComparison.OrdinalIgnoreCase);
''','state-aware buttons')
s=sub(s,r'''            if \(text\.Contains\("select before operate".*?            if \(text\.Contains\("direct operate".*?            \{\n                return "DO";\n            \}\n''','''            if ((text.Contains("select before operate", StringComparison.OrdinalIgnoreCase) || text.Contains("SBO", StringComparison.OrdinalIgnoreCase)) && text.Contains("enhanced", StringComparison.OrdinalIgnoreCase)) return "SBO • Enhanced security";
            if (text.Contains("select before operate", StringComparison.OrdinalIgnoreCase) || text.Contains("SBO", StringComparison.OrdinalIgnoreCase)) return "SBO • Normal security";
            if ((text.Contains("direct operate", StringComparison.OrdinalIgnoreCase) || text.Contains("(DO)", StringComparison.OrdinalIgnoreCase)) && text.Contains("enhanced", StringComparison.OrdinalIgnoreCase)) return "Direct • Enhanced security";
            if (text.Contains("direct operate", StringComparison.OrdinalIgnoreCase) || text.Contains("(DO)", StringComparison.OrdinalIgnoreCase)) return "Direct • Normal security";
''','control model security text')
s=one(s,'Interval = TimeSpan.FromMilliseconds(500)','Interval = TimeSpan.FromMilliseconds(1500)','timer load')
s=one(s,'Converter = CommandButtonEnabledConverter.Instance,\n            Mode','Converter = CommandButtonEnabledConverter.Instance,\n            ConverterParameter = content,\n            Mode','converter parameter')
s=one(s,'enabledBinding.Bindings.Add(new Binding(nameof(SignalDefinition.ControlSupportsOperate)));','enabledBinding.Bindings.Add(new Binding(nameof(SignalDefinition.ControlSupportsOperate)));\n        enabledBinding.Bindings.Add(new Binding(nameof(SignalDefinition.ControlCurrentValue)));','current binding')
write(p,s)

p='MainWindow.xaml.cs'; s=read(p)
s=one(s,'await RefreshControlValuesAsync(SelectedDevice);','await RefreshControlValuesAsync(SelectedDevice, force: true);','panel refresh')
s=sub(s,r'''  if \(signal\.ControlModelText == "Auto-detect" \|\| signal\.ControlCurrentValue == "-"\)\n  \{.*?  \}\n\n  var result = await _runtime\.ExecuteControlAsync\(''','''  var capabilities = await _runtime.InspectControlAsync(device.DeviceId, signal, _applicationCancellation.Token);
  signal.ControlCurrentValue = capabilities.CurrentValue;
  device.RefreshCommandSignalProjection();
  RebuildControlFeedbackIndex(device);
  if (!capabilities.SupportsOperate)
      throw new InvalidOperationException($"{signal.ObjectReference} is not command-ready: {capabilities.ControlModelText}.");
  if (!CommandTestMode && SameControlState(signal, requestedValue, capabilities.CurrentValue))
  {
      var current = string.IsNullOrWhiteSpace(capabilities.CurrentValue) ? "the requested state" : capabilities.CurrentValue;
      signal.ControlLastResult = $"Already {current} — no command was sent.";
      SetStatus($"{device.Name}: {signal.Name} is already {current}; duplicate control suppressed.");
      return;
  }

  var result = await _runtime.ExecuteControlAsync(''','live preflight')
s=one(s,'    private static string BuildQuickControlResult(Iec61850ControlCommandResult result)','''    private static bool SameControlState(SignalDefinition signal, string requested, string current)
    {
        if (signal.IsPositionControl && Iec61850ValueFormatter.TryNormalizeDbpos(requested, out var requestCode) && Iec61850ValueFormatter.TryNormalizeDbpos(current, out var currentCode)) return requestCode == currentCode;
        if (signal.IsBooleanControl && bool.TryParse(requested, out var requestBool) && bool.TryParse(current, out var currentBool)) return requestBool == currentBool;
        return requested.Trim().Equals(current.Trim(), StringComparison.OrdinalIgnoreCase);
    }

    private static string BuildQuickControlResult(Iec61850ControlCommandResult result)''','state helper')
write(p,s)

p='MainWindow.xaml'; s=read(p)
for a,b,n in [
('<ColumnDefinition Width="250"/>','<ColumnDefinition Width="258"/>','explorer width'),
('''                            <Grid DockPanel.Dock="Top" Margin="0,0,0,10">
                                <StackPanel>
                                    <StackPanel Orientation="Horizontal">
                                        <Ellipse Width="8" Height="8" Fill="{StaticResource Accent}" Margin="0,0,8,0" VerticalAlignment="Center"/>
                                        <TextBlock Text="IED Explorer" FontSize="15.5" FontWeight="SemiBold" Foreground="{StaticResource Ink}"/>
                                    </StackPanel>
                                    <TextBlock Text="Independent MMS session per IED" FontSize="11.8" Foreground="{StaticResource Muted}" Margin="16,3,0,0"/>
                                </StackPanel>
                            </Grid>''','''                            <Grid DockPanel.Dock="Top" Margin="0,0,0,8">
                                <StackPanel Orientation="Horizontal">
                                    <Ellipse Width="8" Height="8" Fill="{StaticResource Accent}" Margin="0,0,8,0" VerticalAlignment="Center"/>
                                    <TextBlock Text="IED Explorer" FontSize="15.5" FontWeight="SemiBold" Foreground="{StaticResource Ink}"/>
                                </StackPanel>
                            </Grid>''','subtitle'),
('<ColumnDefinition Width="8"/>','<ColumnDefinition Width="6"/>','button gap'),
('<Button Grid.Column="0" Click="ConnectAllIeds_Click" Style="{StaticResource SoftButton}"','<Button Grid.Column="0" Click="ConnectAllIeds_Click" Style="{StaticResource SoftButton}" Padding="8,7" FontSize="11.5"','connect fit'),
('<Viewbox Width="14" Height="14" Margin="0,0,6,0">','<Viewbox Width="13" Height="13" Margin="0,0,4,0">','connect icon'),
('<Button Grid.Column="2" Click="AddRelay_Click" Style="{StaticResource PrimaryButton}"','<Button Grid.Column="2" Click="AddRelay_Click" Style="{StaticResource PrimaryButton}" Padding="8,7" FontSize="11.5"','add fit'),
('CornerRadius="15" Padding="10">\n                                                        <ContentPresenter/>','CornerRadius="14" Padding="8">\n                                                        <ContentPresenter/>','card padding'),
('<Grid MinHeight="86">','<Grid MinHeight="72">','card height'),
('<ColumnDefinition Width="64"/>','<ColumnDefinition Width="66"/>','icon column'),
('Width="58" Height="58" Margin="0,-2,6,0" VerticalAlignment="Top"','Width="62" Height="62" Margin="0,0,4,0" VerticalAlignment="Center"','icon center'),
('<Viewbox Width="55" Height="55"','<Viewbox Width="60" Height="60"','icon size'),
('HorizontalAlignment="Left" Margin="0,7,0,0"','HorizontalAlignment="Left" Margin="0,4,0,0"','action spacing'),
('<DataGridTextColumn Header="Signal" Binding="{Binding SignalName}" Width="220*" MinWidth="175"/>','<DataGridTextColumn Header="Signal" Binding="{Binding SignalName}" Width="1.05*" MinWidth="145"/>','signal width'),
('<DataGridTextColumn Header="IEC Telegram" Binding="{Binding IecTelegram}" Width="320*" MinWidth="250"/>','<DataGridTextColumn Header="IEC Telegram" Binding="{Binding IecTelegram}" Width="1.55*" MinWidth="205"/>','telegram width'),
('<DataGridTextColumn Header="Value" Binding="{Binding Value}" Width="120*" MinWidth="100"/>','<DataGridTextColumn Header="Value" Binding="{Binding Value}" Width="0.8*" MinWidth="125"/>','value width'),
('<DataGridTextColumn Header="Quality" Binding="{Binding Quality}" Width="150*" MinWidth="125"/>','<DataGridTextColumn Header="Quality" Binding="{Binding Quality}" Width="0.72*" MinWidth="105"/>','quality width'),
('<DataGridTextColumn Header="IED Timestamp" Binding="{Binding DeviceTimestamp}" Width="185*" MinWidth="150"/>','<DataGridTextColumn Header="IED Timestamp" Binding="{Binding DeviceTimestamp}" Width="1.05*" MinWidth="155"/>','timestamp width'),
('<DataGridTextColumn Header="Acquisition" Binding="{Binding SourceMode}" Width="190*" MinWidth="160"/>','<DataGridTextColumn Header="Acquisition" Binding="{Binding SourceMode}" Width="1.05*" MinWidth="150"/>','acquisition width'),
('<DataGridTextColumn Header="IEC Telegram" Binding="{Binding DisplayReference}" Width="280" IsReadOnly="True"/>','<DataGridTextColumn Header="IEC Telegram" Binding="{Binding DisplayReference}" Width="2.1*" MinWidth="210" IsReadOnly="True"/>','command telegram'),
('<DataGridTemplateColumn Header="Value" Width="115">','<DataGridTemplateColumn Header="Value" Width="0.85*" MinWidth="105">','command value'),
('<DataGridTextColumn Header="CDC / Type" Binding="{Binding ControlCdc}" Width="105" IsReadOnly="True"/>','<DataGridTextColumn Header="CDC / Type" Binding="{Binding ControlCdc}" Width="0.72*" MinWidth="88" IsReadOnly="True"/>','command cdc'),
('<DataGridTextColumn Header="Control model" Binding="{Binding ControlModelText}" Width="210" IsReadOnly="True"/>','<DataGridTextColumn Header="Control model" Binding="{Binding ControlModelText}" Width="1.35*" MinWidth="175" IsReadOnly="True"/>','command model'),
('<DataGridTemplateColumn Header="Control" Width="*" MinWidth="220">','<DataGridTemplateColumn Header="Control" Width="1.45*" MinWidth="200">','command control')]:
    s=one(s,a,b,n)
write(p,s)
