using System.Globalization;
using System.Net;
using System.Xml;
using System.Xml.Linq;

namespace ArIED61850Tester.Services;

public sealed record SclIedEndpoint(
    string IedName,
    string AccessPointName,
    string IpAddress,
    int Port,
    string SubNetworkName)
{
    public string EndpointText => $"{IpAddress}:{Port}";
}

public sealed class SclImportResult
{
    public string SourceFilePath { get; init; } = string.Empty;
    public int IedDefinitionCount { get; init; }
    public int ConnectedAccessPointCount { get; init; }
    public IReadOnlyList<SclIedEndpoint> Endpoints { get; init; } = Array.Empty<SclIedEndpoint>();
    public IReadOnlyList<string> Warnings { get; init; } = Array.Empty<string>();
}

/// <summary>
/// Reads IEC 61850 SCL communication data without trusting external entities.
/// The importer is namespace-version agnostic and extracts IED/AP/IP endpoint
/// identity only; the live IED model is still verified through MMS discovery.
/// </summary>
public static class SclImportService
{
    private static readonly string[] IpParameterNames =
    {
        "IP", "IPv4", "IPv6", "IP-Address", "IPAddress"
    };

    private static readonly string[] PortParameterNames =
    {
        "MMS-Port", "MMS_PORT", "IP-Port", "TCP-Port", "Port"
    };

    public static Task<SclImportResult> LoadAsync(string filePath, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(filePath);
        return Task.Run(() => Load(filePath, cancellationToken), cancellationToken);
    }

    private static SclImportResult Load(string filePath, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!File.Exists(filePath))
            throw new FileNotFoundException("The selected SCL file no longer exists.", filePath);

        var settings = new XmlReaderSettings
        {
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null,
            IgnoreComments = true,
            IgnoreProcessingInstructions = true,
            IgnoreWhitespace = true,
            CloseInput = true
        };

        XDocument document;
        using (var stream = File.OpenRead(filePath))
        using (var reader = XmlReader.Create(stream, settings))
            document = XDocument.Load(reader, LoadOptions.None);

        cancellationToken.ThrowIfCancellationRequested();
        var root = document.Root ?? throw new InvalidDataException("The selected XML document is empty.");
        if (!NameIs(root, "SCL"))
            throw new InvalidDataException("The selected XML document is not an IEC 61850 SCL file (missing SCL root element).");

        var warnings = new List<string>();
        var iedNames = root
            .Descendants()
            .Where(element => NameIs(element, "IED"))
            .Select(element => AttributeValue(element, "name"))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var connectedAccessPoints = root
            .Descendants()
            .Where(element => NameIs(element, "ConnectedAP"))
            .ToArray();

        var endpoints = new List<SclIedEndpoint>();
        var endpointKeys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var connectedAp in connectedAccessPoints)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var iedName = AttributeValue(connectedAp, "iedName");
            var accessPointName = AttributeValue(connectedAp, "apName");
            var subNetworkName = connectedAp
                .Ancestors()
                .FirstOrDefault(element => NameIs(element, "SubNetwork")) is { } subNetwork
                ? AttributeValue(subNetwork, "name")
                : string.Empty;

            if (string.IsNullOrWhiteSpace(iedName))
            {
                warnings.Add("A ConnectedAP entry was ignored because its iedName attribute is empty.");
                continue;
            }

            if (iedNames.Count > 0 && !iedNames.Contains(iedName))
                warnings.Add($"ConnectedAP '{iedName}/{accessPointName}' does not match an IED definition in the file; its endpoint was still imported.");

            var parameters = ReadAddressParameters(connectedAp).ToArray();
            var ipText = FindParameter(parameters, IpParameterNames);
            if (string.IsNullOrWhiteSpace(ipText))
            {
                warnings.Add($"{iedName}/{DisplayAccessPoint(accessPointName)} has no IP address in its ConnectedAP Address block.");
                continue;
            }

            if (!IPAddress.TryParse(ipText, out var parsedIp))
            {
                warnings.Add($"{iedName}/{DisplayAccessPoint(accessPointName)} has an invalid IP address '{ipText}'.");
                continue;
            }

            var port = 102;
            var portText = FindParameter(parameters, PortParameterNames);
            if (!string.IsNullOrWhiteSpace(portText) &&
                (!int.TryParse(portText, NumberStyles.Integer, CultureInfo.InvariantCulture, out port) || port is <= 0 or > 65535))
            {
                warnings.Add($"{iedName}/{DisplayAccessPoint(accessPointName)} has invalid MMS port '{portText}'; TCP 102 was used.");
                port = 102;
            }

            var canonicalIp = parsedIp.ToString();
            var key = $"{canonicalIp}|{port}";
            if (!endpointKeys.Add(key))
            {
                warnings.Add($"Duplicate endpoint {canonicalIp}:{port} for {iedName}/{DisplayAccessPoint(accessPointName)} was ignored.");
                continue;
            }

            endpoints.Add(new SclIedEndpoint(
                iedName,
                accessPointName,
                canonicalIp,
                port,
                subNetworkName));
        }

        return new SclImportResult
        {
            SourceFilePath = Path.GetFullPath(filePath),
            IedDefinitionCount = iedNames.Count,
            ConnectedAccessPointCount = connectedAccessPoints.Length,
            Endpoints = endpoints
                .OrderBy(endpoint => endpoint.IedName, StringComparer.OrdinalIgnoreCase)
                .ThenBy(endpoint => endpoint.AccessPointName, StringComparer.OrdinalIgnoreCase)
                .ThenBy(endpoint => endpoint.IpAddress, StringComparer.OrdinalIgnoreCase)
                .ToArray(),
            Warnings = warnings.ToArray()
        };
    }

    private static IEnumerable<KeyValuePair<string, string>> ReadAddressParameters(XElement connectedAp)
    {
        var address = connectedAp.Elements().FirstOrDefault(element => NameIs(element, "Address")) ??
                      connectedAp.Descendants().FirstOrDefault(element => NameIs(element, "Address"));
        if (address == null)
            yield break;

        foreach (var parameter in address.Elements().Where(element => NameIs(element, "P")))
        {
            var type = AttributeValue(parameter, "type");
            var value = parameter.Value.Trim();
            if (!string.IsNullOrWhiteSpace(type) && !string.IsNullOrWhiteSpace(value))
                yield return new KeyValuePair<string, string>(type, value);
        }
    }

    private static string FindParameter(
        IReadOnlyCollection<KeyValuePair<string, string>> parameters,
        IEnumerable<string> candidateNames)
    {
        foreach (var candidate in candidateNames)
        {
            var value = parameters.FirstOrDefault(parameter =>
                parameter.Key.Equals(candidate, StringComparison.OrdinalIgnoreCase)).Value;
            if (!string.IsNullOrWhiteSpace(value))
                return value.Trim();
        }

        return string.Empty;
    }

    private static bool NameIs(XElement element, string localName)
        => element.Name.LocalName.Equals(localName, StringComparison.OrdinalIgnoreCase);

    private static string AttributeValue(XElement element, string localName)
        => element.Attributes()
               .FirstOrDefault(attribute => attribute.Name.LocalName.Equals(localName, StringComparison.OrdinalIgnoreCase))
               ?.Value.Trim() ?? string.Empty;

    private static string DisplayAccessPoint(string accessPointName)
        => string.IsNullOrWhiteSpace(accessPointName) ? "unnamed AP" : accessPointName;
}
