from pathlib import Path
import re
p=Path('Services/Iec61850MonitorRuntime.cs')
s=p.read_text(encoding='utf-8')
def one(a,b,n):
 global s
 c=s.count(a)
 if c!=1: raise RuntimeError(f'{n}: {c}')
 s=s.replace(a,b,1)
def sub(a,b,n):
 global s
 s,c=re.subn(a,b,s,count=1,flags=re.S)
 if c!=1: raise RuntimeError(f'{n}: {c}')

one('''        public DateTime NextReconnectUtc { get; set; } = DateTime.MinValue;
        public int ConsecutiveSessionErrors { get; set; }
''','''        public DateTime NextReconnectUtc { get; set; } = DateTime.MinValue;
        public int ConsecutiveSessionErrors { get; set; }
        public DateTime LastSuccessfulIoUtc { get; set; } = DateTime.UtcNow;
        public DateTime NextHealthProbeUtc { get; set; } = DateTime.MinValue;
        public int ConsecutiveHealthProbeFailures { get; set; }
        public string HealthProbePointKey { get; set; } = string.Empty;
''','session liveness')
one('''        session.ConsecutiveSessionErrors = 0;

        var safePollMs''','''        session.ConsecutiveSessionErrors = 0;
        session.LastSuccessfulIoUtc = DateTime.UtcNow;
        session.NextHealthProbeUtc = DateTime.UtcNow.AddSeconds(1);
        session.ConsecutiveHealthProbeFailures = 0;
        session.HealthProbePointKey = string.Empty;

        var safePollMs''','liveness reset')
one('''        var plans = Iec61850ReportPlanner.BuildPlans(device, session.Points.Values);
''','''        session.HealthProbePointKey = session.Points.Values
            .OrderByDescending(IsFastPoint)
            .ThenBy(point => point.SignalName, StringComparer.OrdinalIgnoreCase)
            .Select(point => point.PointKey)
            .FirstOrDefault() ?? string.Empty;

        var plans = Iec61850ReportPlanner.BuildPlans(device, session.Points.Values);
''','heartbeat point')
one('''                if (!session.Client.IsConnected)
                {
                    await TryReconnectAsync(session, cancellationToken).ConfigureAwait(false);
                    await Task.Delay(250, cancellationToken).ConfigureAwait(false);
                    continue;
                }

                await ReceiveReportSlicesAsync(session, cancellationToken).ConfigureAwait(false);
                await PollDuePointsAsync(session, cancellationToken).ConfigureAwait(false);
                await TryStartPendingReportSetupAsync(session, cancellationToken).ConfigureAwait(false);
                session.ConsecutiveSessionErrors = 0;
''','''                if (!session.Client.IsConnected)
                {
                    MarkSessionOffline(session, "IEC 61850 transport is offline; smart reconnect is pending.");
                    await TryReconnectAsync(session, cancellationToken).ConfigureAwait(false);
                    await Task.Delay(200, cancellationToken).ConfigureAwait(false);
                    continue;
                }

                await ReceiveReportSlicesAsync(session, cancellationToken).ConfigureAwait(false);
                await PollDuePointsAsync(session, cancellationToken).ConfigureAwait(false);
                await ProbeSessionHealthAsync(session, cancellationToken).ConfigureAwait(false);
                await TryStartPendingReportSetupAsync(session, cancellationToken).ConfigureAwait(false);
''','monitor loop')
one('''                if (session.ConsecutiveSessionErrors >= 5)
                    await ForceReconnectAsync(session).ConfigureAwait(false);
''','''                if (session.ConsecutiveSessionErrors >= 2)
                    await ForceReconnectAsync(session, "Repeated monitor I/O failures.").ConfigureAwait(false);
''','reconnect threshold')
one('''        session.Device.Detail = session.ActiveReportPlans.Count > 0
            ? $"{session.Points.Count} point(s): live values started by MMS, then report-first acquisition was armed; MMS remains for q/t and low-rate verification."
            : $"{session.Points.Count} point(s): reporting could not be armed; MMS polling fallback remains active.";
''','''        session.Device.Detail = session.ActiveReportPlans.Count > 0
            ? $"{session.Points.Count} point(s): event-driven reporting is primary; one lightweight MMS heartbeat and low-rate verification keep connection health reliable."
            : $"{session.Points.Count} point(s): reporting could not be armed; bounded MMS polling fallback remains active.";
''','summary')
one('var defaultDelay = session.ActiveReportPlans.Count > 0 ? 5 : 10;','var defaultDelay = session.ActiveReportPlans.Count > 0 ? 12 : 25;','loop delay')
one('''        if (remainingMs <= 0)
            return 1;
        return Math.Clamp((int)Math.Ceiling(remainingMs), 1, defaultDelay);
''','''        if (remainingMs <= 0)
            return 2;
        return Math.Clamp((int)Math.Ceiling(remainingMs), 2, defaultDelay);
''','minimum delay')
one('var batchCount = Math.Min(plans.Count, 8);','var batchCount = Math.Min(plans.Count, 4);','report batch')
one('TimeSpan.FromMilliseconds(4),','TimeSpan.FromMilliseconds(3),','report slice')
one('''            ProcessReportHealth(session, plan, slice);

            foreach (var update in slice.Updates)
''','''            ProcessReportHealth(session, plan, slice);
            if (slice.ReportFrames.Count > 0 || slice.Updates.Count > 0)
                RecordSuccessfulIo(session);

            foreach (var update in slice.Updates)
''','report io')
one('while (processed < 12 && session.PollQueue.TryPeek','while (processed < 8 && session.PollQueue.TryPeek','poll batch')
one('''                state.ConsecutiveErrors = 0;
                if (resolved.UsedAlternateReference(point.IecReference))
''','''                state.ConsecutiveErrors = 0;
                RecordSuccessfulIo(session);
                if (resolved.UsedAlternateReference(point.IecReference))
''','poll io')
one('''                if (state.ConsecutiveErrors >= 5)
                    session.ConsecutiveSessionErrors++;
''','''                if (state.ConsecutiveErrors >= 2)
                    session.ConsecutiveSessionErrors++;
''','point errors')
sub(r'''    private async Task TryReconnectAsync\(DeviceSession session, CancellationToken cancellationToken\)\n    \{.*?\n    \}\n\n    private async Task ForceReconnectAsync\(DeviceSession session\)\n    \{.*?\n    \}\n''','''    private async Task TryReconnectAsync(DeviceSession session, CancellationToken cancellationToken)
    {
        if (DateTime.UtcNow < session.NextReconnectUtc) return;
        session.NextReconnectUtc = DateTime.UtcNow.AddSeconds(2);
        MarkSessionOffline(session, $"Reconnecting MMS association to {session.Device.EndpointText}.");
        session.Device.Status = "Reconnecting";
        Log("WARN", session.Device.Name, "IEC 61850 session is offline. Smart reconnect started.");
        try { await session.Client.DisposeAsync().ConfigureAwait(false); } catch { }
        session.Client = new NativeIec61850Client();
        try { await session.Client.ConnectAsync(session.Device.IpAddress, session.Device.Port, cancellationToken).ConfigureAwait(false); }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            session.Device.Status = "Reconnect pending";
            session.Device.Detail = ex.Message;
            session.Device.RefreshComputed();
            return;
        }
        if (!session.Client.IsConnected)
        {
            session.Device.Status = "Reconnect pending";
            session.Device.Detail = session.Client.LastErrorMessage;
            session.Device.RefreshComputed();
            return;
        }
        session.ActiveReportPlans.Clear();
        session.ActiveReportPlanOrder.Clear();
        session.PointPlanIds.Clear();
        session.ReportStreams.Clear();
        session.LastUnroutedReportCount = 0;
        var plans = Iec61850ReportPlanner.BuildPlans(session.Device, session.Points.Values);
        await StartReportPlansAsync(session, plans, cancellationToken).ConfigureAwait(false);
        ResetPollQueue(session);
        UpdateDeviceAcquisitionSummary(session);
        session.ConsecutiveSessionErrors = 0;
        session.ConsecutiveHealthProbeFailures = 0;
        session.LastSuccessfulIoUtc = DateTime.UtcNow;
        session.NextHealthProbeUtc = DateTime.UtcNow.AddSeconds(1);
        session.Device.IsConnected = true;
        session.Device.Status = "Monitoring";
        session.Device.Detail = $"MMS reconnected. {session.Points.Count} point(s) resumed.";
        session.Device.RefreshComputed();
        Log("INFO", session.Device.Name, "MMS reconnect successful. Monitoring resumed automatically.");
    }

    private async Task ForceReconnectAsync(DeviceSession session, string reason)
    {
        MarkSessionOffline(session, reason);
        session.ConsecutiveSessionErrors = 0;
        session.ConsecutiveHealthProbeFailures = 0;
        session.NextReconnectUtc = DateTime.MinValue;
        try { await session.Client.DisposeAsync().ConfigureAwait(false); } catch { }
    }

    private void RecordSuccessfulIo(DeviceSession session)
    {
        session.LastSuccessfulIoUtc = DateTime.UtcNow;
        session.ConsecutiveHealthProbeFailures = 0;
        session.ConsecutiveSessionErrors = 0;
    }

    private void MarkSessionOffline(DeviceSession session, string detail)
    {
        var wasConnected = session.Device.IsConnected;
        session.Device.IsConnected = false;
        session.Device.Status = "Offline";
        session.Device.Detail = detail;
        session.Device.AcquisitionMode = "Connection lost • reconnect pending";
        session.Device.RefreshComputed();
        if (wasConnected) Log("WARN", session.Device.Name, detail);
    }

    private async Task ProbeSessionHealthAsync(DeviceSession session, CancellationToken cancellationToken)
    {
        var now = DateTime.UtcNow;
        if (now < session.NextHealthProbeUtc || now - session.LastSuccessfulIoUtc < TimeSpan.FromMilliseconds(900)) return;
        session.NextHealthProbeUtc = now.AddSeconds(1);
        if (string.IsNullOrWhiteSpace(session.HealthProbePointKey) || !session.Points.TryGetValue(session.HealthProbePointKey, out var point))
        {
            point = session.Points.Values.FirstOrDefault();
            if (point == null) return;
            session.HealthProbePointKey = point.PointKey;
        }
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromMilliseconds(900));
        try
        {
            var signal = new SignalDefinition { Name = point.SignalName, ObjectReference = point.IecReference, FunctionalConstraint = point.FunctionalConstraint, DataType = point.IecDataType, Category = point.Category, Unit = point.Unit };
            if (await IecSignalReadResolver.ReadAsync(session.Client, signal, timeout.Token).ConfigureAwait(false) != null)
            {
                RecordSuccessfulIo(session);
                return;
            }
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { }
        catch (Exception ex) when (ex is not OperationCanceledException) { Log("WARN", session.Device.Name, $"MMS health probe failed: {ex.Message}"); }
        session.ConsecutiveHealthProbeFailures++;
        if (session.ConsecutiveHealthProbeFailures >= 2)
            await ForceReconnectAsync(session, "IED stopped responding to two consecutive MMS health probes.").ConfigureAwait(false);
    }
''','reconnect and heartbeat')
one('''        if (!reportAssigned || !state.ReportChangeVerified)
            return point.PollingIntervalMs;

        // Once an actual dchg/qchg/dupd edge is observed, report is primary. Keep a
        // lightweight safety read so a misconfigured or later-stalled RCB cannot freeze
        // the tester silently. Fast status points are validated more often than analogs.
        var minimum = IsFastPoint(point) ? 5000 : 15000;
        return Math.Clamp(Math.Max(point.PollingIntervalMs * 10, minimum), minimum, 60000);
''','''        if (!reportAssigned) return point.PollingIntervalMs;
        if (state.ReportTrafficSeen)
        {
            var minimum = state.ReportChangeVerified ? (IsFastPoint(point) ? 10000 : 30000) : (IsFastPoint(point) ? 5000 : 15000);
            return Math.Clamp(Math.Max(point.PollingIntervalMs * 15, minimum), minimum, 60000);
        }
        var awaitingReportMinimum = IsFastPoint(point) ? 2000 : 5000;
        return Math.Clamp(Math.Max(point.PollingIntervalMs * 3, awaitingReportMinimum), awaitingReportMinimum, 15000);
''','event first intervals')
p.write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
