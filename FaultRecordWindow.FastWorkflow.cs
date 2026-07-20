using System.Windows.Threading;

namespace ArIED61850Tester;

public partial class FaultRecordWindow
{
    private bool _initialFastWorkflowObserved;

    /// <summary>
    /// The existing Loaded handler starts discovery automatically. This post-render
    /// guard keeps the window responsive, waits for that first scan, and performs one
    /// bounded reconnect/rescan when the initial automatic discovery fails.
    /// </summary>
    protected override async void OnContentRendered(EventArgs e)
    {
        base.OnContentRendered(e);
        if (_initialFastWorkflowObserved)
            return;

        _initialFastWorkflowObserved = true;
        await Dispatcher.Yield(DispatcherPriority.ContextIdle);

        while (IsBusy && IsVisible)
            await Task.Delay(50).ConfigureAwait(true);

        if (!IsVisible || Records.Count > 0 ||
            !StatusText.StartsWith("Fault-record scan failed", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        StatusText = "Automatic file discovery is reconnecting and retrying once…";
        await Task.Delay(250).ConfigureAwait(true);
        if (IsVisible && !IsBusy)
            await ScanAsync().ConfigureAwait(true);
    }
}