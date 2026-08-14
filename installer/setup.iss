; Inno Setup Skript fuer PitBoss
; Baut aus dist\PitBoss\ einen Windows-Installer.
; Version kommt aus der Umgebungsvariable APP_VERSION (in CI aus dem Git-Tag).
#define AppName "PitBoss"
#ifndef AppVer
  #define AppVer GetEnv("APP_VERSION")
#endif
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=PitBoss
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName} {#AppVer}
OutputDir=Output
OutputBaseFilename=PitBoss-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=..\assets\lmu_app_icon.ico
UninstallDisplayIcon={app}\PitBoss.exe

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "..\dist\PitBoss\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PitBoss.exe"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\PitBoss.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PitBoss.exe"; Description: "{#AppName} starten"; Flags: nowait postinstall skipifsilent
