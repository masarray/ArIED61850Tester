using System.Collections.Concurrent;
using System.Globalization;
using System.Windows;
using ArIED61850Tester.Models;
using ArIED61850Tester.Services;

namespace ArIED61850Tester;

public partial class MainWindow
{
    private const int MaxGooseTimelineEvents = 1000;
    private const int MaxPendingGooseTimelineEvents = 4096;

    private readonly ConcurrentQueue<GooseSubscriberFrameSnapshot> _pendingGooseTimeline = new();
    private readonly Dictionary<string, DateTimeOffset> _lastGooseTimelineTimestamp = new(StringComparer.OrdinalIgnoreCase);
    private GooseEventRow? _selectedGooseEvent;

    public BulkObservableCollection<GooseEventRow> GooseEvents { get; } = new();

    public GooseEventRow? SelectedGooseEvent
    {
        get => _selectedGooseEvent;
        set
        {
            if (!Set(ref _selectedGooseEvent, value))
                return;

            if (value is not null && _gooseStreamIndex.TryGetValue(value.StreamKey, out var stream))
                SelectedGooseStream = stream;
        }
    }

    public string GoosePublisherCountText => $"{GooseStreams.Count:N0}";
    public string GooseEventCountText => $"{GooseEvents.Count:N0}";
    public string GooseSelectedLeafCountText => $"{SelectedGooseStream?.Leaves.Count ?? 0:N0} values";
    public Visibility GooseNoEventsVisibility => GooseEvents.Count == 0 ? Visibility.Visible : Visibility.Collapsed;

    private void QueueGooseTimelineEvent(GooseSubscriberFrameSnapshot snapshot)
    {
        if (!IsMeaningfulGooseTimelineEvent(snapshot))
            return;

        _pendingGooseTimeline.Enqueue(snapshot);
        while (_pendingGooseTimeline.Count > MaxPendingGooseTimelineEvents && _pendingGooseTimeline.TryDequeue(out _))
        {
        }
    }

    private static bool IsMeaningfulGooseTimelineEvent(GooseSubscriberFrameSnapshot snapshot)
    {
        if (snapshot.PacketCount <= 1 || snapshot.StreamEvent.ChangedValueCount > 0 || snapshot.StreamEvent.Diagnostics.Count > 0)
            return true;

        var status = snapshot.StreamEvent.GooseSequenceStatus.ToString();
        return status.Contains("State", StringComparison.OrdinalIgnoreCase) ||
               (!status.Contains("Retransmission", StringComparison.OrdinalIgnoreCase) &&
                !status.Contains("Normal", StringComparison.OrdinalIgnoreCase));
    }

    private void FlushGooseTimelineUi()
    {
        var processed = 0;
        while (processed < 256 && _pendingGooseTimeline.TryDequeue(out var captured))
        {
            var stream = BuildGooseStreamSnapshot(captured, _gooseBindingCatalog);
            var eventRow = BuildGooseEventRow(captured, stream);
            GooseEvents.Insert(0, eventRow);
            while (GooseEvents.Count > MaxGooseTimelineEvents)
                GooseEvents.RemoveAt(GooseEvents.Count - 1);

            SelectedGooseEvent ??= eventRow;
            processed++;
        }

        RaiseGoosePresentationState();
    }

    private GooseEventRow BuildGooseEventRow(
        GooseSubscriberFrameSnapshot captured,
        GooseStreamSnapshot stream)
    {
        var status = stream.SequenceStatus;
        var hasDiagnostics = !string.IsNullOrWhiteSpace(stream.DiagnosticsSummary);
        var isNew = captured.PacketCount <= 1;
        var isStateChange = stream.ChangedValueCount > 0 || status.Contains("State", StringComparison.OrdinalIgnoreCase);

        var eventText = isNew
            ? "New"
            : hasDiagnostics
                ? "Warning"
                : isStateChange
                    ? "State change"
                    : FriendlySequenceStatus(status);
        var eventTone = hasDiagnostics
            ? "Warning"
            : isStateChange
                ? "Change"
                : "Info";

        var deltaText = "-";
        if (_lastGooseTimelineTimestamp.TryGetValue(captured.StreamKey, out var previousTimestamp))
        {
            var delta = captured.CaptureTimestamp - previousTimestamp;
            deltaText = FormatGooseDelta(delta);
        }
        _lastGooseTimelineTimestamp[captured.StreamKey] = captured.CaptureTimestamp;

        return new GooseEventRow
        {
            StreamKey = captured.StreamKey,
            Timestamp = captured.CaptureTimestamp,
            DeltaText = deltaText,
            EventText = eventText,
            EventTone = eventTone,
            Publisher = BuildGoosePublisherName(stream),
            StateSequenceText = $"{stream.StateNumberText} / {stream.SequenceNumberText}",
            Summary = BuildGooseEventSummary(stream, isNew, hasDiagnostics)
        };
    }

    private static string BuildGoosePublisherName(GooseStreamSnapshot stream)
    {
        foreach (var candidate in new[] { stream.ModelIedName, stream.GoId, ShortGooseReference(stream.GoCbRef), stream.AppIdText })
        {
            if (!string.IsNullOrWhiteSpace(candidate))
                return candidate;
        }

        return "GOOSE publisher";
    }

    private static string BuildGooseEventSummary(GooseStreamSnapshot stream, bool isNew, bool hasDiagnostics)
    {
        if (hasDiagnostics)
            return ShortenGooseText(stream.DiagnosticsSummary, 150);

        var changed = stream.Leaves
            .Where(leaf => leaf.IsChanged)
            .Take(2)
            .Select(leaf =>
            {
                var previous = string.IsNullOrWhiteSpace(leaf.PreviousValue) ? "-" : ShortenGooseText(leaf.PreviousValue, 30);
                return $"{leaf.SignalName}: {previous} → {ShortenGooseText(leaf.Value, 36)}";
            })
            .ToArray();
        if (changed.Length > 0)
        {
            var suffix = stream.ChangedValueCount > changed.Length
                ? $" • +{stream.ChangedValueCount - changed.Length:N0} more"
                : string.Empty;
            return string.Join(" • ", changed) + suffix;
        }

        if (isNew)
            return $"Publisher detected • {stream.Leaves.Count:N0} DataSet value(s)";

        return FriendlySequenceStatus(stream.SequenceStatus);
    }

    private static string FriendlySequenceStatus(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return "GOOSE update";

        var text = value.Replace("_", " ");
        var result = new System.Text.StringBuilder(text.Length + 8);
        for (var index = 0; index < text.Length; index++)
        {
            if (index > 0 && char.IsUpper(text[index]) && char.IsLower(text[index - 1]))
                result.Append(' ');
            result.Append(text[index]);
        }
        return result.ToString();
    }

    private static string FormatGooseDelta(TimeSpan delta)
    {
        if (delta.TotalMilliseconds < 1000)
            return $"{Math.Max(0, delta.TotalMilliseconds):0.0} ms";
        if (delta.TotalSeconds < 60)
            return $"{delta.TotalSeconds:0.000} s";
        return delta.ToString(@"mm\:ss\.fff", CultureInfo.InvariantCulture);
    }

    private static string ShortGooseReference(string? value)
    {
        var text = value?.Trim() ?? string.Empty;
        var slash = text.LastIndexOf('/');
        if (slash >= 0 && slash < text.Length - 1)
            text = text[(slash + 1)..];
        return text.Replace('$', '.');
    }

    private static string ShortenGooseText(string? value, int maximumLength)
    {
        var text = value?.Trim() ?? string.Empty;
        if (text.Length <= maximumLength)
            return text;
        return text[..Math.Max(1, maximumLength - 1)] + "…";
    }

    private void ResetGooseTimelineUi()
    {
        while (_pendingGooseTimeline.TryDequeue(out _))
        {
        }
        _lastGooseTimelineTimestamp.Clear();
        GooseEvents.Clear();
        SelectedGooseEvent = null;
        RaiseGoosePresentationState();
    }

    private void RaiseGoosePresentationSelection()
    {
        Raise(nameof(GooseSelectedLeafCountText));
    }

    private void RaiseGoosePresentationState()
    {
        Raise(nameof(GoosePublisherCountText));
        Raise(nameof(GooseEventCountText));
        Raise(nameof(GooseSelectedLeafCountText));
        Raise(nameof(GooseNoEventsVisibility));
    }
}
