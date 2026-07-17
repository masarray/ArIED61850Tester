using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using ArIED61850Tester.Models;

namespace ArIED61850Tester;

public partial class SmvViewerWindow : Window, INotifyPropertyChanged
{
    private SmvStreamRow? _selectedStream;

    public SmvViewerWindow(Iec61850MonitorDevice device)
    {
        ArgumentNullException.ThrowIfNull(device);
        InitializeComponent();

        DeviceId = device.DeviceId;
        DeviceName = device.Name;
        EndpointText = string.IsNullOrWhiteSpace(device.IpAddress)
            ? "MMS endpoint unassigned"
            : $"{device.IpAddress}:{device.Port}";

        var rows = BuildRows(device);
        foreach (var row in rows)
            Streams.Add(row);

        SelectedStream = Streams.FirstOrDefault();
        StatusText = Streams.Count == 0
            ? "No Sampled Value control block is configured in the opened SCL model or discovered from this IED."
            : $"{Streams.Count:N0} Sampled Value stream definition(s) are available for this IED.";
        DataContext = this;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public string DeviceId { get; }
    public string DeviceName { get; }
    public string EndpointText { get; }
    public ObservableCollection<SmvStreamRow> Streams { get; } = new();
    public string StatusText { get; }
    public string StreamCountText => $"{Streams.Count:N0} stream(s)";

    public SmvStreamRow? SelectedStream
    {
        get => _selectedStream;
        set
        {
            if (ReferenceEquals(_selectedStream, value))
                return;
            _selectedStream = value;
            Raise();
            Raise(nameof(SelectedStreamDetail));
        }
    }

    public string SelectedStreamDetail => SelectedStream == null
        ? "Select a stream to inspect its engineering identity and DataSet coverage."
        : $"{SelectedStream.Source} • {SelectedStream.ControlReference} • DataSet {SelectedStream.DataSetReference} • {SelectedStream.MemberCount} member(s).";

    private static IReadOnlyList<SmvStreamRow> BuildRows(Iec61850MonitorDevice device)
    {
        var rows = new List<SmvStreamRow>();

        if (device.SclWorkspace is { } workspace)
        {
            rows.AddRange(workspace.SampledValuesStreams.Select(stream => new SmvStreamRow
            {
                Source = "SCL",
                ControlReference = stream.ControlBlockReference,
                StreamId = FirstNonEmpty(stream.SmvId, stream.SvId),
                DataSetReference = stream.DataSetReference,
                AppId = stream.Address.AppIdText,
                DestinationMac = stream.Address.DestinationMacText,
                Vlan = stream.Address.VlanId?.ToString() ?? "-",
                SampleRate = stream.SampleRate == 0 ? "-" : stream.SampleRate.ToString(),
                SampleMode = string.IsNullOrWhiteSpace(stream.SampleMode) ? "-" : stream.SampleMode,
                NumberOfAsdu = stream.NoAsdu.ToString(),
                MemberCount = stream.Entries.Count
            }));
        }

        if (device.LiveDiscoveryModel is { } liveModel)
        {
            rows.AddRange(liveModel.SampledValueControlBlocks.Select(control => new SmvStreamRow
            {
                Source = "Live discovery",
                ControlReference = control.Reference,
                StreamId = FirstNonEmpty(control.SmvId, control.ControlId),
                DataSetReference = control.DataSetReference,
                AppId = string.IsNullOrWhiteSpace(control.AppId) ? "-" : control.AppId,
                DestinationMac = "-",
                Vlan = "-",
                SampleRate = string.IsNullOrWhiteSpace(control.SampleRate) ? "-" : control.SampleRate,
                SampleMode = string.IsNullOrWhiteSpace(control.SampleMode) ? "-" : control.SampleMode,
                NumberOfAsdu = string.IsNullOrWhiteSpace(control.NumberOfAsdu) ? "-" : control.NumberOfAsdu,
                MemberCount = FindMemberCount(liveModel, control.DataSetReference)
            }));
        }

        return rows
            .Where(row => !string.IsNullOrWhiteSpace(row.ControlReference) || !string.IsNullOrWhiteSpace(row.StreamId))
            .GroupBy(
                row => $"{Normalize(row.ControlReference)}|{Normalize(row.StreamId)}|{Normalize(row.DataSetReference)}",
                StringComparer.OrdinalIgnoreCase)
            .Select(group => group
                .OrderByDescending(row => row.Source.Equals("SCL", StringComparison.OrdinalIgnoreCase))
                .First())
            .OrderBy(row => row.ControlReference, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    private static int FindMemberCount(
        AR.Iec61850.Discovery.LiveIedModelDiscoveryDocument model,
        string dataSetReference)
    {
        if (string.IsNullOrWhiteSpace(dataSetReference))
            return 0;

        var normalized = Normalize(dataSetReference);
        return model.DataSets.FirstOrDefault(dataSet => Normalize(dataSet.Reference) == normalized)?.MemberCount ?? 0;
    }

    private static string FirstNonEmpty(params string[] values)
        => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value))?.Trim() ?? "-";

    private static string Normalize(string? value)
        => (value ?? string.Empty).Trim().Replace('$', '.').ToLowerInvariant();

    private void Close_Click(object sender, RoutedEventArgs e)
        => Close();

    private void Raise([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

public sealed class SmvStreamRow
{
    public string Source { get; init; } = string.Empty;
    public string ControlReference { get; init; } = string.Empty;
    public string StreamId { get; init; } = string.Empty;
    public string DataSetReference { get; init; } = string.Empty;
    public string AppId { get; init; } = string.Empty;
    public string DestinationMac { get; init; } = string.Empty;
    public string Vlan { get; init; } = string.Empty;
    public string SampleRate { get; init; } = string.Empty;
    public string SampleMode { get; init; } = string.Empty;
    public string NumberOfAsdu { get; init; } = string.Empty;
    public int MemberCount { get; init; }
}