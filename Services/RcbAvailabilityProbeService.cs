using AR.Iec61850.Mms;
using ArIED61850Tester.Models;

namespace ArIED61850Tester.Services;

/// <summary>
/// Opens a short-lived, read-only MMS association for an explicit RCB availability audit.
/// No report attribute is written and no RCB is reserved or enabled.
/// </summary>
public sealed class RcbAvailabilityProbeService
{
    public async Task<MmsRcbAvailabilityResult> CheckAsync(
        Iec61850MonitorDevice device,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(device);
        if (string.IsNullOrWhiteSpace(device.IpAddress))
            throw new InvalidOperationException("Bind an MMS endpoint before checking RCB availability.");

        await using var session = new MmsClientSession();
        await session.ConnectAsync(
            device.IpAddress,
            device.Port <= 0 ? 102 : device.Port,
            TimeSpan.FromSeconds(8),
            cancellationToken).ConfigureAwait(false);
        if (!session.IsMmsInitiated)
            throw new InvalidOperationException("The read-only RCB audit association did not reach MMS Initiated state.");

        var discovery = await session.DiscoverAsync(
            probeReportAttributes: true,
            maxReportAttributeProbes: 512,
            cancellationToken).ConfigureAwait(false);

        var callerOwned = device.Points
            .Select(point => point.ReportControlReference)
            .Concat(device.Signals.Where(signal => signal.IsSelected).Select(signal => signal.ReportControlReference))
            .Where(reference => !string.IsNullOrWhiteSpace(reference))
            .Select(reference => reference.Trim())
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        return await session.CheckReportControlAvailabilityAsync(
            discovery.ReportInventory,
            discovery.IedDirectory,
            new MmsRcbAvailabilityOptions
            {
                MaxReportControls = 512,
                ReadDataSetDirectories = true,
                CallerOwnedRcbReferences = callerOwned
            },
            cancellationToken).ConfigureAwait(false);
    }
}
