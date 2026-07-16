from pathlib import Path

adapter_path = Path("MainWindow.DemoGooseData.cs")
adapter_text = adapter_path.read_text(encoding="utf-8")
start = adapter_text.index('                Name = "')
end = adapter_text.index('\n', start)
adapter_text = adapter_text[:start] + '                Name = "station-bus-ethernet-1",' + adapter_text[end:]
adapter_path.write_text(adapter_text, encoding="utf-8")

control_path = Path("Models/ControlModels.cs")
control_text = control_path.read_text(encoding="utf-8")
control_text = control_text.replace("namespace ARSASTester.Models;", "namespace ArIED61850Tester.Models;")
control_path.write_text(control_text, encoding="utf-8")

diagnostic_path = Path("Services/DiagnosticReportBuilder.cs")
diagnostic_text = diagnostic_path.read_text(encoding="utf-8")
diagnostic_text = diagnostic_text.replace("using ARSASTester.Models;", "using ArIED61850Tester.Models;")
diagnostic_text = diagnostic_text.replace("namespace ARSASTester.Services;", "namespace ArIED61850Tester.Services;")
diagnostic_path.write_text(diagnostic_text, encoding="utf-8")

print("Applied generated-source compile corrections.")
