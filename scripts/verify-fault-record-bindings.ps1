$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$xamlPath = Join-Path $root 'FaultRecordWindow.xaml'
$xaml = Get-Content $xamlPath -Raw

$requiredOneWayBindings = @(
    'DeviceName',
    'EndpointText',
    'IsNotBusy',
    'SelectionSummary',
    'Records',
    'RecordName',
    'ModifiedText',
    'SizeText',
    'FilesText',
    'Completeness',
    'StatusText',
    'ProgressValue',
    'IsIndeterminate',
    'IsBusy',
    'CanDownload'
)

foreach ($property in $requiredOneWayBindings) {
    $pattern = "\{Binding\s+$([regex]::Escape($property))\s*,[^}]*Mode=OneWay[^}]*\}"
    if ($xaml -notmatch $pattern) {
        throw "FaultRecordWindow display binding '$property' must explicitly use Mode=OneWay."
    }
}

$requiredTwoWayBindings = @('RemoteDirectory', 'DestinationDirectory', 'IsSelected')
foreach ($property in $requiredTwoWayBindings) {
    $pattern = "\{Binding\s+$([regex]::Escape($property))\s*,[^}]*Mode=TwoWay[^}]*\}"
    if ($xaml -notmatch $pattern) {
        throw "FaultRecordWindow editable binding '$property' must explicitly use Mode=TwoWay."
    }
}

Write-Host 'Fault record binding modes are explicit and valid.'
