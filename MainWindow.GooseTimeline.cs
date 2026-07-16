using System.Collections.Concurrent;
using System.ComponentModel;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using ArIED61850Tester.Models;
using ArIED61850Tester.Services;
using ArIED61850Tester.Views;

namespace ArIED61850Tester;

public partial class MainWindow
{
    private const int MaxGooseTimelineEvents = 300;
    private const int MaxPendingGooseTimelineEvents = 512;

    private readonly ConcurrentQueue<GooseSubscriberFrameSnapshot> _pendingGooseTimeline = new();
    private readonly Dictionary<string, DateTimeOffset> _lastGooseTimelineTimestamp = new(StringComparer.OrdinalIgnoreCase);
    private GooseEventRow? _selectedGooseEvent;
    private bool _goosePresentationInstalled;
    private DateTimeOffset _nextGooseHighlightExpiryCheckUtc = DateTimeOffset.MinValue;

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

    [ModuleInitializer]
    internal static void RegisterGoosePresentationIntegration()
    {
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnMainWindowLoadedForGoosePresentation));
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            GooseSubscriberLiteView.RefreshAdaptersRequestedEvent,
            new RoutedEventHandler(OnRefreshGooseAdaptersRequested));
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            GooseSubscriberLiteView.RefreshModelsRequestedEvent,
            new RoutedEventHandler(OnRefreshGooseModelsRequested));
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            GooseSubscriberLiteView.StartRequestedEvent,
            new RoutedEventHandler(OnStartGooseRequested));
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            GooseSubscriberLiteView.StopRequestedEvent,
            new RoutedEventHandler(OnStopGooseRequested));
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            GooseSubscriberLiteView.ClearRequestedEvent,
            new RoutedEventHandler(OnClearGooseRequested));
    }

    private static void OnMainWindowLoadedForGoosePresentation(object sender, RoutedEventArgs args)
    {
        if (sender is MainWindow window && ReferenceEquals(args.OriginalSource, window))
            window.InstallGoosePresentationWorkspace();
    }

    private void InstallGoosePresentationWorkspace()
    {
        if (_goosePresentationInstalled)
            return;

        var gooseTab = MainTabs.Items
            .OfType<TabItem>()
            .FirstOrDefault(item => string.Equals(item.Header?.ToString(), "GOOSE Subscriber", StringComparison.Ordinal));
        if (gooseTab is null)
            return;

        gooseTab.Content = new GooseSubscriberLiteView { DataContext = this };
        _gooseSubscriberRuntime.FrameReceived += GooseTimeline_FrameReceived;
        _uiFlushTimer.Tick += GooseTimelineUiFlushTimer_Tick;
        PropertyChanged += GoosePresentation_PropertyChanged;
        _goosePresentationInstalled = true;
        RaiseGoosePresentationState();
    }

    private void GoosePresentation_PropertyChanged(object? sender, PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(SelectedGooseStream))
            Raise(nameof(GooseSelectedLeafCountText));
    }

    private static void OnRefreshGooseAdaptersRequested(object sender, RoutedEventArgs args)
    {
        if (sender is not MainWindow window)
            return;
        window.RefreshGooseAdapters_Click(window, args);
        args.Handled = true;
    }

    private static void OnRefreshGooseModelsRequested(object sender, RoutedEventArgs args)
    {
        if (sender is not MainWindow window)
            return;
        window.RefreshGooseModels_Click(window, args);
        args.Handled = true;
    }

    private static void OnStartGooseRequested(object sender, RoutedEventArgs args)
    {
        if (sender is not MainWindow window)
            return;
        window.ResetGooseTimelineUi();
        window.StartGooseSubscriber_Click(window, args);
        args.Handled = true;
    }

    private static void OnStopGooseRequested(object sender, RoutedEventArgs args)
    {
        if (sender is not MainWindow window)
            return;
        window.StopGooseSubscriber_Click(window, args);
        args.Handled = true;
    }

    private static void OnClearGooseRequested(object sender, RoutedEventArgs args)
    {
        if (sender is not MainWindow window)
            return;
        window.ResetGooseTimelineUi();
        window.ClearGooseSubscriber_Click(window, args);
        args.Handled = true;
    }

    private void GooseTimeline_FrameReceived(GooseSubscriberFrameSnapshot snapshot)
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

    private void GooseTimelineUiFlushTimer_Tick(object? sender, EventArgs args)
    {
        var nowUtc = DateTimeOffset.UtcNow;
        if (nowUtc >= _nextGooseHighlightExpiryCheckUtc)
        {
            ExpireGooseHighlights(nowUtc);
            _nextGooseHighlightExpiryCheckUtc = nowUtc.AddSeconds(1);
        }

        if (_pendingGooseTimeline.IsEmpty)
            return;

        var processed = 0;
        while (processed < 48 && _pendingGooseTimeline.TryDequeue(out var captured))
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

    private void ExpireGooseHighlights(DateTimeOffset nowUtc)
    {
        foreach (var eventRow in GooseEvents)
            eventRow.ExpireHighlight(nowUtc);

        foreach (var stream in GooseStreams)
        {
            foreach (var leaf in stream.Leaves)
                leaf.ExpireHighlight(nowUtc);
        }
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
        _nextGooseHighlightExpiryCheckUtc = DateTimeOffset.MinValue;
        GooseEvents.Clear();
        SelectedGooseEvent = null;
        RaiseGoosePresentationState();
    }

    private void RaiseGoosePresentationState()
    {
        Raise(nameof(GoosePublisherCountText));
        Raise(nameof(GooseEventCountText));
        Raise(nameof(GooseSelectedLeafCountText));
        Raise(nameof(GooseNoEventsVisibility));
    }
}
