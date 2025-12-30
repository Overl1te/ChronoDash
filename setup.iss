; Script generated for ChronoDash
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "ChronoDash"
#define MyAppVersion "2.2.7-beta"
#define MyAppPublisher "Overl1te"
#define MyAppURL "https://github.com/Overl1te/ChronoDash"
#define MyAppExeName "ChronoDash.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{7D19B64D-3EBA-4F80-98AD-F6FAFD81396D}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
DirExistsWarning=no
OutputBaseFilename=ChronoDash_Setup_v{#MyAppVersion}
OutputDir=installers
SetupIconFile=assets\icons\chronodash.ico
LicenseFile=C:\Users\vboxuser\Desktop\ChronoDash\LICENSE
InfoBeforeFile=C:\Users\vboxuser\Desktop\ChronoDash\TERMS_OF_USE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern polar
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
Source: "build\main.dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent