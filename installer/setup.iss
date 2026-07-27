; Inno Setup Skript fuer LMU Consistency Coach
; Baut aus dist\LMU Consistency Coach\ einen Windows-Installer.
; Version kommt aus der Umgebungsvariable APP_VERSION (in CI aus dem Git-Tag).
#define AppName "LMU Consistency Coach"
#ifndef AppVer
  #define AppVer GetEnv("APP_VERSION")
#endif
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=LMU Consistency Coach
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName} {#AppVer}
OutputDir=Output
OutputBaseFilename=LMU-Consistency-Coach-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=..\assets\lmu_app_icon.ico
UninstallDisplayIcon={app}\LMU Consistency Coach.exe

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "..\dist\LMU Consistency Coach\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\LMU Consistency Coach.exe"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\LMU Consistency Coach.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LMU Consistency Coach.exe"; Description: "{#AppName} starten"; Flags: nowait postinstall skipifsilent
