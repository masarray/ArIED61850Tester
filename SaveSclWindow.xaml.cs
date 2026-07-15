using System.Windows;
using AR.Iec61850.Scl.Export;

namespace ArIED61850Tester;

public sealed class SaveSclDialogViewModel
{
    public SaveSclDialogViewModel(
        string iedName,
        string sourceDescription,
        SclSchemaProfile selectedProfile = SclSchemaProfile.Edition2V31)
    {
        IedName = string.IsNullOrWhiteSpace(iedName) ? "IED" : iedName.Trim();
        SourceDescription = string.IsNullOrWhiteSpace(sourceDescription)
            ? "IEC 61850 model"
            : sourceDescription.Trim();
        SchemaProfiles =
        [
            SclSchemaProfiles.Get(SclSchemaProfile.Edition2V31),
            SclSchemaProfiles.Get(SclSchemaProfile.Edition1V16)
        ];
        SelectedSchemaProfile = SclSchemaProfiles.Get(selectedProfile);
    }

    public string IedName { get; }
    public string SourceDescription { get; }
    public IReadOnlyList<SclSchemaProfileDescriptor> SchemaProfiles { get; }
    public SclSchemaProfileDescriptor SelectedSchemaProfile { get; set; }
}

public partial class SaveSclWindow : Window
{
    public SaveSclWindow(
        string iedName,
        string sourceDescription,
        SclSchemaProfile selectedProfile = SclSchemaProfile.Edition2V31)
    {
        InitializeComponent();
        DataContext = new SaveSclDialogViewModel(iedName, sourceDescription, selectedProfile);
    }

    public SaveSclDialogViewModel ViewModel => (SaveSclDialogViewModel)DataContext;

    private void Save_Click(object sender, RoutedEventArgs e)
        => DialogResult = true;
}
