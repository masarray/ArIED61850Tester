from pathlib import Path

path = Path("MainWindow.DemoGooseData.cs")
text = path.read_text(encoding="utf-8")
start = text.index('                Name = "')
end = text.index('\n', start)
text = text[:start] + '                Name = "station-bus-ethernet-1",' + text[end:]
path.write_text(text, encoding="utf-8")
print("Applied generated-source compile corrections.")
