; Inno Setup script for 知枝 (Knowledge Tree) — WORK-2026-035 slice 3b.
; Build via scripts/build_installer.py, which passes /DAppVersion and /DSourceDir.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\zhizhi"
#endif

[Setup]
AppId={{8F2B3C1E-6A7D-4E9B-9C2A-1D5E4F0B8A6C}
AppName=知枝
AppVersion={#AppVersion}
AppPublisher=Knowledge Tree
AppPublisherURL=https://example.invalid/zhizhi
DefaultDirName={localappdata}\Programs\知枝
DefaultGroupName=知枝
UninstallDisplayIcon={app}\zhizhi.exe
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=zhizhi-{#AppVersion}-setup
SetupIconFile=icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Optional code signing: uncomment and configure a sign tool + certificate.
; Inno Setup runs the command once per compiled/signed file; leave disabled when
; no certificate is available (build still succeeds).
; SignTool=zsign /d $q知枝$q $f

[Files]
; The frozen onedir bundle, placed under {app}. User data lives in
; %LOCALAPPDATA%\知枝\data (outside {app}), so upgrades and uninstall never
; touch it. `ignoreversion` + `recursesubdirs` make upgrades overwrite in place.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\知枝"; Filename: "{app}\zhizhi.exe"; WorkingDir: "{app}"; IconFilename: "{app}\zhizhi.exe"
Name: "{group}\卸载 知枝"; Filename: "{uninstallexe}"
Name: "{autodesktop}\知枝"; Filename: "{app}\zhizhi.exe"; Tasks: desktopicon; IconFilename: "{app}\zhizhi.exe"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Run]
Filename: "{app}\zhizhi.exe"; Description: "启动 知枝"; Flags: nowait postinstall skipifsilent
