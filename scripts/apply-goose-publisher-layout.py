from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


root = Path('.')
main_path = root / 'MainWindow.xaml'
models_path = root / 'Models' / 'GooseSubscriberModels.cs'
goose_code_path = root / 'MainWindow.GooseSubscriber.cs'
workflow_path = root / '.github' / 'workflows' / 'build.yml'

main = main_path.read_text(encoding='utf-8')
models = models_path.read_text(encoding='utf-8')
goose_code = goose_code_path.read_text(encoding='utf-8')
workflow = workflow_path.read_text(encoding='utf-8')

if 'xmlns:views="clr-namespace:ArIED61850Tester.Views"' not in main:
    main = replace_once(
        main,
        '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n',
        '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n        xmlns:views="clr-namespace:ArIED61850Tester.Views"\n',
        'views namespace')

goose_tab = '''            <!-- BEGINNER-READABLE GOOSE WORKSPACE -->
            <TabItem Header="GOOSE Subscriber">
                <views:GooseSubscriberView
                    RefreshAdaptersRequested="RefreshGooseAdapters_Click"
                    RefreshModelsRequested="RefreshGooseModels_Click"
                    StartRequested="StartGooseSubscriber_Click"
                    StopRequested="StopGooseSubscriber_Click"
                    ClearRequested="ClearGooseSubscriber_Click"/>
            </TabItem>

'''
main, count = re.subn(
    r'            <!-- SCL / DISCOVERY-AWARE GOOSE SUBSCRIBER -->\n            <TabItem Header="GOOSE Subscriber">.*?            </TabItem>\n\n(?=            <!-- DIAGNOSTICS -->)',
    goose_tab,
    main,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError(f'GOOSE tab replacement: expected one match, found {count}')

models = replace_once(
    models,
    'public sealed class GooseStreamRow : ObservableObject',
    'public sealed partial class GooseStreamRow : ObservableObject',
    'partial GooseStreamRow')
models = replace_once(
    models,
    '        Raise(nameof(HealthText));\n',
    '        Raise(nameof(HealthText));\n        RaisePresentationProperties();\n',
    'presentation property notification')

goose_code = replace_once(
    goose_code,
    '            Raise(nameof(GooseNoLeafValuesVisibility));\n',
    '            Raise(nameof(GooseNoLeafValuesVisibility));\n            RaiseGoosePresentationSelection();\n',
    'selection presentation notification')
goose_code = replace_once(
    goose_code,
    '        SelectedGooseStream = null;\n        if (resetCounters)\n',
    '        SelectedGooseStream = null;\n        ResetGooseTimelineUi();\n        if (resetCounters)\n',
    'timeline reset')
goose_code = replace_once(
    goose_code,
    '    private void GooseSubscriberRuntime_FrameReceived(GooseSubscriberFrameSnapshot snapshot)\n        => _pendingGooseFrames[snapshot.StreamKey] = snapshot;\n',
    '''    private void GooseSubscriberRuntime_FrameReceived(GooseSubscriberFrameSnapshot snapshot)
    {
        _pendingGooseFrames[snapshot.StreamKey] = snapshot;
        QueueGooseTimelineEvent(snapshot);
    }
''',
    'timeline queue')
goose_code = replace_once(
    goose_code,
    '        if (_pendingGooseFrames.IsEmpty)\n            return;\n',
    '        if (_pendingGooseFrames.IsEmpty && _pendingGooseTimeline.IsEmpty)\n            return;\n',
    'flush guard')
goose_code = replace_once(
    goose_code,
    '        Raise(nameof(GooseCounterText));\n        Raise(nameof(GooseNoStreamsVisibility));\n',
    '        FlushGooseTimelineUi();\n        Raise(nameof(GooseCounterText));\n        Raise(nameof(GooseNoStreamsVisibility));\n',
    'timeline UI flush')

if '$gooseView = Get-Content' not in workflow:
    workflow = replace_once(
        workflow,
        '          $gooseModels = Get-Content .\\ArIED61850Tester\\Models\\GooseSubscriberModels.cs -Raw\n',
        '          $gooseModels = Get-Content .\\ArIED61850Tester\\Models\\GooseSubscriberModels.cs -Raw\n          $gooseView = Get-Content .\\ArIED61850Tester\\Views\\GooseSubscriberView.xaml -Raw\n          $gooseTimeline = Get-Content .\\ArIED61850Tester\\MainWindow.GooseTimeline.cs -Raw\n          $goosePresentation = Get-Content .\\ArIED61850Tester\\Models\\GoosePresentationModels.cs -Raw\n',
        'GOOSE UI validation inputs')

old_visual = '''              $main -notmatch '<TabItem Header="GOOSE Subscriber">' -or
              $main -notmatch 'ItemsSource="\\{Binding SelectedGooseStream.Leaves\\}"' -or
              $main -notmatch 'Header="confRev"' -or
              $main -notmatch 'Header="Flags"' -or
              $main -notmatch 'Header="Diagnostics" Binding="\\{Binding DiagnosticsSummary\\}"' -or'''
new_visual = '''              $main -notmatch '<TabItem Header="GOOSE Subscriber">' -or
              $main -notmatch '<views:GooseSubscriberView' -or
              $gooseView -notmatch 'ItemsSource="\\{Binding GooseStreams\\}"' -or
              $gooseView -notmatch 'ItemsSource="\\{Binding GooseEvents\\}"' -or
              $gooseView -notmatch 'ItemsSource="\\{Binding SelectedGooseStream.Leaves\\}"' -or
              $gooseView -notmatch 'GOOSE Inspector' -or
              $gooseView -notmatch 'State changes &amp; warnings' -or'''
workflow = replace_once(workflow, old_visual, new_visual, 'GOOSE visual invariants')

old_runtime = '''              $gooseModels -notmatch 'FlagsText' -or
              $project -notmatch 'ArIec61850NpcapProject' -or'''
new_runtime = '''              $gooseModels -notmatch 'FlagsText' -or
              $gooseModels -notmatch 'partial class GooseStreamRow' -or
              $gooseTimeline -notmatch 'ConcurrentQueue<GooseSubscriberFrameSnapshot>' -or
              $gooseTimeline -notmatch 'BuildGooseEventSummary' -or
              $goosePresentation -notmatch 'class GooseEventRow' -or
              $project -notmatch 'ArIec61850NpcapProject' -or'''
workflow = replace_once(workflow, old_runtime, new_runtime, 'GOOSE timeline invariants')

if 'ArIED61850Tester/MainWindow.GooseTimeline.cs' not in workflow:
    workflow = replace_once(
        workflow,
        '            ArIED61850Tester/MainWindow.GooseSubscriber.cs\n',
        '            ArIED61850Tester/MainWindow.GooseSubscriber.cs\n            ArIED61850Tester/MainWindow.GooseTimeline.cs\n',
        'timeline snapshot')
if '            ArIED61850Tester/Views\n' not in workflow:
    workflow = replace_once(
        workflow,
        '            ArIED61850Tester/Services\n',
        '            ArIED61850Tester/Services\n            ArIED61850Tester/Views\n',
        'views snapshot')

for token in (
    '<views:GooseSubscriberView',
    'public sealed partial class GooseStreamRow',
    'QueueGooseTimelineEvent(snapshot)',
    '$gooseView = Get-Content',
):
    if token not in main + models + goose_code + workflow:
        raise RuntimeError(f'missing generated invariant: {token}')

main_path.write_text(main, encoding='utf-8')
models_path.write_text(models, encoding='utf-8')
goose_code_path.write_text(goose_code, encoding='utf-8')
workflow_path.write_text(workflow, encoding='utf-8')
print('Applied beginner-readable GOOSE publisher, timeline and inspector integration.')
