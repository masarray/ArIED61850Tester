# Windows release automation

ArIED 61850 publishes two Windows x64 deliverables from the same self-contained multi-file build:

- `ArIED61850-<version>-win-x64-portable.zip` — extract and keep the complete folder together.
- `ArIED61850-<version>-win-x64-setup.exe` — Inno Setup installer with Start Menu integration, optional desktop shortcut, upgrade/uninstall support, and the same GOOSE runtime dependencies as the portable package.

## Automatic tagged release

Push a semantic-version tag to create a GitHub Release automatically:

```powershell
git tag v1.6.16
git push origin v1.6.16
```

The `Release Windows packages` workflow will:

1. checkout ArIED and ARIEC61850;
2. publish the self-contained Windows x64 application;
3. verify the ARIEC61850 Npcap transport, SharpPcap, and PacketDotNet assemblies;
4. build the portable ZIP;
5. compile the Inno Setup installer;
6. perform a silent install/uninstall smoke test;
7. create `SHA256SUMS.txt`;
8. create or update the GitHub Release and upload all three assets.

The tag version is injected into the executable, installer metadata, filenames, and GitHub Release title. Pre-release tags such as `v1.7.0-rc.1` are marked as pre-releases.

## Manual release build

Run **Actions → Release Windows packages → Run workflow**. Enter the version and choose whether GitHub should create a release. Leaving `publish_release` disabled produces downloadable workflow artifacts without creating a public release.

## Installer behavior

The installer:

- installs the complete multi-file application under Program Files by default;
- supports a current-user override from the setup privilege dialog or command line;
- creates a Start Menu shortcut;
- offers an optional desktop shortcut;
- registers a standard Windows uninstaller;
- preserves upgrade compatibility through a stable Inno Setup `AppId`;
- checks whether Npcap is present and explains that it is needed only for GOOSE capture.

Npcap is not bundled. Install it separately according to its license and the engineering workstation policy. MMS, SCL, monitoring, and other non-GOOSE features remain available without Npcap.

## Local installer build

Prerequisites:

- .NET 8 SDK;
- ARIEC61850 repository beside the ArIED repository;
- Inno Setup 6.

```powershell
.\scripts\publish-windows-portable.ps1 -Version 1.6.16
.\scripts\build-windows-installer.ps1 -Version 1.6.16
```

The installer is written to `dist/ArIED61850-1.6.16-win-x64-setup.exe`.

## Release signing

The current workflow produces deterministic unsigned packages. Before production distribution in a managed enterprise environment, sign `ArIED61850.exe` and the final setup executable with an organization-controlled Authenticode certificate and trusted timestamp service. Never commit a PFX file or certificate password to the repository.
