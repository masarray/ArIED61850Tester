using AR.Iec61850.FaultRecords;
using AR.Iec61850.Mms;

namespace ArIED61850Tester.Services;

/// <summary>
/// Owns a short-lived IEC 61850 association dedicated to remote fault-record browsing and download.
/// Keeping this session separate prevents large file transfers from blocking live monitoring traffic.
/// </summary>
public sealed class FaultRecordTransferClient : IAsyncDisposable
{
    private readonly MmsClientSession _session = new();
    private readonly SemaphoreSlim _operationGate = new(1, 1);
    private Iec61850FaultRecordService? _service;
    private string _host = string.Empty;
    private int _port = 102;

    public bool IsConnected => IsSessionHealthy();
    public string ConnectionState =>
        $"{_session.State}; transport={_session.IsTransportConnected}; pump={_session.IsReceivePumpRunning}";

    public async Task ConnectAsync(
        string host,
        int port,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(host);
        var normalizedHost = host.Trim();
        var normalizedPort = port <= 0 ? 102 : port;

        await _operationGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var sameEndpoint =
                _host.Equals(normalizedHost, StringComparison.OrdinalIgnoreCase) &&
                _port == normalizedPort;
            if (sameEndpoint && IsSessionHealthy())
                return;

            // The connection operation token must not own the lifetime of a reusable MMS
            // receive pump. A completed scan token is replaced before download; without this
            // rebind the old cancellation would stop confirmed-service response routing while
            // the association still appeared to be MmsInitiated.
            if (_session.IsTransportConnected ||
                _session.IsMmsInitiated ||
                _session.IsReceivePumpRunning)
            {
                await _session.DisposeAsync().ConfigureAwait(false);
            }

            await _session.ConnectAsync(
                normalizedHost,
                normalizedPort,
                TimeSpan.FromSeconds(8),
                cancellationToken).ConfigureAwait(false);
            await _session.RebindReceivePumpToSessionLifetimeAsync(cancellationToken).ConfigureAwait(false);

            if (!IsSessionHealthy())
            {
                throw new InvalidOperationException(
                    $"The dedicated fault-record association is not operational after connect. {ConnectionState}.");
            }

            _host = normalizedHost;
            _port = normalizedPort;
            _service = new Iec61850FaultRecordService(_session);
        }
        finally
        {
            _operationGate.Release();
        }
    }

    public async Task<Iec61850FaultRecordCatalog> DiscoverAsync(
        string? remoteDirectory,
        CancellationToken cancellationToken = default)
    {
        await _operationGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            EnsureReady();
            return await _service!.DiscoverAsync(
                remoteDirectory,
                new Iec61850FaultRecordDiscoveryOptions
                {
                    TraverseSubdirectories = true,
                    MaximumDirectoryDepth = 4,
                    MaximumDirectoryCount = 128,
                    MaximumEntries = 20_000,
                    MaximumPagesPerDirectory = 32
                },
                cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _operationGate.Release();
        }
    }

    public async Task<Iec61850FaultRecordDownloadResult> DownloadAsync(
        Iec61850FaultRecordSet record,
        string destinationRoot,
        IProgress<Iec61850FaultRecordDownloadProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(record);
        ArgumentException.ThrowIfNullOrWhiteSpace(destinationRoot);

        await _operationGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            EnsureReady();
            return await _service!.DownloadAsync(
                record,
                destinationRoot,
                new Iec61850FaultRecordDownloadOptions
                {
                    MaximumTotalBytes = 1024L * 1024L * 1024L,
                    MaximumFileBytes = 512L * 1024L * 1024L,
                    MaximumReadOperationsPerFile = 100_000,
                    // Completeness describes COMTRADE companion coverage; it must not block
                    // MMS FileOpen/FileRead of files that the IED actually exposes.
                    RequireCompleteRecord = false,
                    RequireDeclaredSizeMatch = false
                },
                progress,
                cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _operationGate.Release();
        }
    }

    public async ValueTask DisposeAsync()
    {
        await _operationGate.WaitAsync().ConfigureAwait(false);
        try
        {
            _service = null;
            await _session.DisposeAsync().ConfigureAwait(false);
        }
        finally
        {
            _operationGate.Release();
            _operationGate.Dispose();
        }
    }

    private bool IsSessionHealthy()
        => _session.IsMmsInitiated &&
           _session.IsTransportConnected &&
           _session.IsReceivePumpRunning;

    private void EnsureReady()
    {
        if (!IsSessionHealthy() || _service == null)
        {
            throw new InvalidOperationException(
                $"The dedicated fault-record association is not ready. {ConnectionState}.");
        }
    }
}
