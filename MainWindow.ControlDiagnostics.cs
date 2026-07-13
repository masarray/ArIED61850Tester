using System.Collections.Concurrent;
using System.ComponentModel;
using System.Text.RegularExpressions;
using ArIED61850Tester.Models;

namespace ArIED61850Tester;

public partial class MainWindow
{
    private static readonly TimeSpan CswiCloseDebounce = TimeSpan.FromMilliseconds(350);
    private static readonly TimeSpan ControlFeedbackStateLifetime = TimeSpan.FromSeconds(15);

    private static readonly Regex ControlRequestedPattern = new(
        @"Control requested:\s*(?<reference>.+?)\s+value=(?<value>[^;]+);",
        RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);

    private sealed class PendingCswiCloseSnapshot
    {
        public required Iec61850PointSnapshot Latest { get; set; }
        public CancellationTokenSource Cancellation { get; } = new();
        public object Sync { get; } = new();
    }

    private sealed class ActivePositionCloseCommand
    {
        public required string Key { get; init; }
        public required SignalDefinition Signal { get; init; }
        public required string BeforeValue { get; init; }
        public DateTimeOffset StartedUtc { get; init; } = DateTimeOffset.UtcNow;
        public bool Restoring { get; set; }
        public PropertyChangedEventHandler? PropertyChangedHandler { get; set; }
    }

    private readonly ConcurrentDictionary<string, PendingCswiCloseSnapshot> _pendingCswiCloseSnapshots =
        new(StringComparer.OrdinalIgnoreCase);

    private readonly ConcurrentDictionary<string, DateTimeOffset> _stableClosedPositionReferences =
        new(StringComparer.OrdinalIgnoreCase);

    private readonly Dictionary<string, ActivePositionCloseCommand> _activePositionCloseCommands =
        new(StringComparer.OrdinalIgnoreCase);

    private bool _controlDiagnosticNormalizerInstalled;

    protected override void OnContentRendered(EventArgs e)
    {
        base.OnContentRendered(e);
        if (_controlDiagnosticNormalizerInstalled)
            return;

        _controlDiagnosticNormalizerInstalled = true;

        // Keep the normal runtime batching path, but filter the short CSWI Close pulse
        // before it reaches the Value Viewer or command-row feedback binding.
        _runtime.PointUpdated -= Runtime_PointUpdated;
        _runtime.PointUpdated += Runtime_PointUpdatedWithStablePositionFilter;

        // ctlModel=StatusOnly is valid read-only model information, not a transport fault.
        _runtime.Diagnostic -= Runtime_Diagnostic;
        _runtime.Diagnostic += Runtime_DiagnosticWithControlModelClassification;
    }

    private void Runtime_PointUpdatedWithStablePositionFilter(Iec61850PointSnapshot snapshot)
    {
        var reference = snapshot.Point.IecReference;
        if (!IsPositionStatusReference(reference))
        {
            Runtime_PointUpdated(snapshot);
            return;
        }

        var key = NormalizeReference(reference);
        var value = NormalizeControlState(snapshot.Value);

        if (!value.Equals("Closed", StringComparison.OrdinalIgnoreCase))
        {
            _stableClosedPositionReferences.TryRemove(key, out _);
            CancelPendingCswiClose(key);
            Runtime_PointUpdated(snapshot);
            return;
        }

        // XCBR/XSWI position is equipment feedback and remains immediate. Only CSWI.Pos
        // is debounced because this relay exposes a short command-object Close echo there.
        if (!IsCswiPositionStatusReference(reference))
        {
            _stableClosedPositionReferences[key] = DateTimeOffset.UtcNow;
            Runtime_PointUpdated(snapshot);
            return;
        }

        if (_pendingCswiCloseSnapshots.TryGetValue(key, out var existing))
        {
            lock (existing.Sync)
                existing.Latest = snapshot;
            return;
        }

        var pending = new PendingCswiCloseSnapshot { Latest = snapshot };
        if (!_pendingCswiCloseSnapshots.TryAdd(key, pending))
        {
            if (_pendingCswiCloseSnapshots.TryGetValue(key, out existing))
            {
                lock (existing.Sync)
                    existing.Latest = snapshot;
            }
            return;
        }

        _ = ReleaseStableCswiCloseAsync(key, pending);
    }

    private async Task ReleaseStableCswiCloseAsync(string key, PendingCswiCloseSnapshot pending)
    {
        try
        {
            await Task.Delay(CswiCloseDebounce, pending.Cancellation.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            return;
        }

        if (!_pendingCswiCloseSnapshots.TryRemove(key, out var active) || !ReferenceEquals(active, pending))
            return;

        Iec61850PointSnapshot stableSnapshot;
        lock (pending.Sync)
            stableSnapshot = pending.Latest;

        _stableClosedPositionReferences[key] = DateTimeOffset.UtcNow;
        Runtime_PointUpdated(stableSnapshot);
    }

    private void CancelPendingCswiClose(string key)
    {
        if (!_pendingCswiCloseSnapshots.TryRemove(key, out var pending))
            return;

        pending.Cancellation.Cancel();
        pending.Cancellation.Dispose();
    }

    private void Runtime_DiagnosticWithControlModelClassification(DiagnosticEntry entry)
    {
        ObserveControlRequest(entry.Message);

        if (IsStatusOnlyControlInspection(entry.Message))
        {
            Runtime_Diagnostic(new DiagnosticEntry
            {
                Time = entry.Time,
                Level = "INFO",
                Source = entry.Source,
                Message = $"{ExtractControlReference(entry.Message)}: ctlModel=StatusOnly; this is a read-only status object and command actions are disabled."
            });
            return;
        }

        if (IsUnknownControlModelInspection(entry.Message))
        {
            Runtime_Diagnostic(new DiagnosticEntry
            {
                Time = entry.Time,
                Level = "WARN",
                Source = entry.Source,
                Message = $"{ExtractControlReference(entry.Message)}: ctlModel could not be resolved; command actions remain disabled until the live model is known."
            });
            return;
        }

        Runtime_Diagnostic(entry);
    }

    private void ObserveControlRequest(string? message)
    {
        if (string.IsNullOrWhiteSpace(message) || Dispatcher.HasShutdownStarted)
            return;

        var match = ControlRequestedPattern.Match(message);
        if (!match.Success)
            return;

        var requestedValue = NormalizeControlState(match.Groups["value"].Value);
        if (!requestedValue.Equals("Closed", StringComparison.OrdinalIgnoreCase))
            return;

        _ = Dispatcher.InvokeAsync(() => BeginPositionCloseCommand(
            match.Groups["reference"].Value,
            requestedValue));
    }

    private void BeginPositionCloseCommand(string reference, string requestedValue)
    {
        var key = NormalizeReference(reference);
        var signal = FindCommandSignal(reference);
        if (string.IsNullOrWhiteSpace(key) || signal == null || !IsPositionCommand(signal) ||
            !requestedValue.Equals("Closed", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        RemovePositionCloseCommand(key);

        var state = new ActivePositionCloseCommand
        {
            Key = key,
            Signal = signal,
            BeforeValue = NormalizeControlState(signal.ControlCurrentValue)
        };

        PropertyChangedEventHandler handler = (_, args) => HandlePositionCloseCommandPropertyChanged(state, args.PropertyName);
        state.PropertyChangedHandler = handler;
        signal.PropertyChanged += handler;
        _activePositionCloseCommands[key] = state;

        // A previous Closed state must not authorize the new command result. Only a fresh
        // live position sample arriving after this request may confirm the new Close.
        var feedbackKey = ResolveControlFeedbackKey(signal);
        if (!string.IsNullOrWhiteSpace(feedbackKey))
            _stableClosedPositionReferences.TryRemove(feedbackKey, out _);

        _ = ExpirePositionCloseCommandAsync(state);
    }

    private void HandlePositionCloseCommandPropertyChanged(ActivePositionCloseCommand state, string? propertyName)
    {
        if (state.Restoring || !_activePositionCloseCommands.TryGetValue(state.Key, out var active) ||
            !ReferenceEquals(active, state))
        {
            return;
        }

        if (propertyName == nameof(SignalDefinition.ControlCurrentValue))
        {
            var current = NormalizeControlState(state.Signal.ControlCurrentValue);
            if (!current.Equals("Closed", StringComparison.OrdinalIgnoreCase))
                return;

            if (HasFreshStableCloseEvidence(state))
            {
                RemovePositionCloseCommand(state.Key);
                state.Signal.ControlLastResult = "Stable process feedback confirmed: Closed.";
                return;
            }

            RestorePreCommandValue(state);
            return;
        }

        if (propertyName != nameof(SignalDefinition.ControlLastResult))
            return;

        var result = state.Signal.ControlLastResult ?? string.Empty;
        if (IsControlFailureResult(result))
        {
            RemovePositionCloseCommand(state.Key);
            return;
        }

        if (!HasFreshStableCloseEvidence(state) &&
            result.Contains("Feedback confirmed", StringComparison.OrdinalIgnoreCase) &&
            result.Contains("Closed", StringComparison.OrdinalIgnoreCase))
        {
            state.Restoring = true;
            try
            {
                state.Signal.ControlLastResult = "Command accepted — waiting for stable Closed process feedback…";
            }
            finally
            {
                state.Restoring = false;
            }
        }
    }

    private void RestorePreCommandValue(ActivePositionCloseCommand state)
    {
        state.Restoring = true;
        try
        {
            state.Signal.ControlCurrentValue = state.BeforeValue;
            state.Signal.ControlLastResult = "Command accepted — waiting for stable Closed process feedback…";
        }
        finally
        {
            state.Restoring = false;
        }
    }

    private bool HasFreshStableCloseEvidence(ActivePositionCloseCommand state)
    {
        var feedbackKey = ResolveControlFeedbackKey(state.Signal);
        return !string.IsNullOrWhiteSpace(feedbackKey) &&
               _stableClosedPositionReferences.TryGetValue(feedbackKey, out var observedUtc) &&
               observedUtc >= state.StartedUtc;
    }

    private static string ResolveControlFeedbackKey(SignalDefinition signal)
    {
        var reference = string.IsNullOrWhiteSpace(signal.ControlStatusReference)
            ? $"{signal.ObjectReference}.stVal"
            : signal.ControlStatusReference;
        return NormalizeReference(reference);
    }

    private async Task ExpirePositionCloseCommandAsync(ActivePositionCloseCommand state)
    {
        await Task.Delay(ControlFeedbackStateLifetime).ConfigureAwait(false);
        if (Dispatcher.HasShutdownStarted)
            return;

        await Dispatcher.InvokeAsync(() =>
        {
            if (!_activePositionCloseCommands.TryGetValue(state.Key, out var active) || !ReferenceEquals(active, state))
                return;

            RemovePositionCloseCommand(state.Key);
            state.Signal.ControlLastResult =
                $"Command accepted, but stable Closed process feedback was not confirmed within {ControlFeedbackStateLifetime.TotalSeconds:0} s.";
        });
    }

    private SignalDefinition? FindCommandSignal(string reference)
    {
        var normalized = NormalizeReference(reference);
        return Devices
            .SelectMany(device => device.CommandSignals)
            .FirstOrDefault(signal => NormalizeReference(signal.ObjectReference)
                .Equals(normalized, StringComparison.OrdinalIgnoreCase));
    }

    private void RemovePositionCloseCommand(string key)
    {
        if (!_activePositionCloseCommands.Remove(key, out var state))
            return;

        if (state.PropertyChangedHandler != null)
            state.Signal.PropertyChanged -= state.PropertyChangedHandler;
    }

    private static bool IsPositionCommand(SignalDefinition signal)
    {
        var reference = (signal.ObjectReference ?? string.Empty).Trim().Replace('$', '.').TrimEnd('.');
        return reference.EndsWith(".Pos", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsPositionStatusReference(string? reference)
    {
        var normalized = (reference ?? string.Empty).Trim().Replace('$', '.').TrimEnd('.');
        return normalized.EndsWith(".Pos.stVal", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsCswiPositionStatusReference(string? reference)
    {
        var normalized = (reference ?? string.Empty).Trim().Replace('$', '.');
        if (!normalized.EndsWith(".Pos.stVal", StringComparison.OrdinalIgnoreCase))
            return false;

        var slash = normalized.LastIndexOf('/');
        var afterSlash = slash >= 0 ? normalized[(slash + 1)..] : normalized;
        var dot = afterSlash.IndexOf('.');
        var logicalNode = dot > 0 ? afterSlash[..dot] : afterSlash;
        return logicalNode.Contains("CSWI", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsControlFailureResult(string result)
        => result.Contains("failed", StringComparison.OrdinalIgnoreCase) ||
           result.Contains("rejected", StringComparison.OrdinalIgnoreCase) ||
           result.Contains("cancelled", StringComparison.OrdinalIgnoreCase) ||
           result.Contains("unsupported", StringComparison.OrdinalIgnoreCase);

    private static string NormalizeControlState(string? value)
    {
        var text = string.IsNullOrWhiteSpace(value) ? "-" : value.Trim();
        if (text.Contains("closed", StringComparison.OrdinalIgnoreCase) ||
            text.Equals("close", StringComparison.OrdinalIgnoreCase) ||
            text.Equals("10", StringComparison.OrdinalIgnoreCase))
        {
            return "Closed";
        }

        if (text.Contains("open", StringComparison.OrdinalIgnoreCase) ||
            text.Equals("01", StringComparison.OrdinalIgnoreCase))
        {
            return "Open";
        }

        if (text.Equals("true", StringComparison.OrdinalIgnoreCase) ||
            text.Equals("on", StringComparison.OrdinalIgnoreCase))
        {
            return "True";
        }

        if (text.Equals("false", StringComparison.OrdinalIgnoreCase) ||
            text.Equals("off", StringComparison.OrdinalIgnoreCase))
        {
            return "False";
        }

        var bracket = text.IndexOf('[');
        return bracket > 0 ? text[..bracket].Trim() : text;
    }

    private static bool IsStatusOnlyControlInspection(string? message)
        => !string.IsNullOrWhiteSpace(message) &&
           message.Contains("Control inspection failed", StringComparison.OrdinalIgnoreCase) &&
           (message.Contains("ctlModel=StatusOnly", StringComparison.OrdinalIgnoreCase) ||
            message.Contains("ctlModel=Status only", StringComparison.OrdinalIgnoreCase));

    private static bool IsUnknownControlModelInspection(string? message)
        => !string.IsNullOrWhiteSpace(message) &&
           message.Contains("Control inspection failed", StringComparison.OrdinalIgnoreCase) &&
           message.Contains("ctlModel=Unknown", StringComparison.OrdinalIgnoreCase);

    private static string ExtractControlReference(string message)
    {
        const string marker = "Control inspection failed for ";
        var start = message.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (start < 0)
            return "IEC 61850 control object";

        start += marker.Length;
        var end = message.IndexOf(':', start);
        var reference = end > start ? message[start..end] : message[start..];
        return string.IsNullOrWhiteSpace(reference) ? "IEC 61850 control object" : reference.Trim();
    }
}
