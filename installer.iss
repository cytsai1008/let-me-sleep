; Inno Setup Script for Let Me Sleep
; Download Inno Setup from: https://jrsoftware.org/isinfo.php
; Icon attribution: Sleep icons created by Freepik - Flaticon
; https://www.flaticon.com/free-icons/sleep

#define MyAppName "Let Me Sleep"
#define MyAppVersion "0.1.3"
#define MyAppPublisher "Let Me Sleep"
#define MyAppURL "https://github.com/cytsai1008/let-me-sleep"
#define MyAppExeName "LetMeSleep.exe"

[Setup]
AppId={{2E61D334-9DF9-4CAB-A041-9C22A083035A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=LetMeSleep_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "scheduledtask"; Description: "Install as scheduled task (enables admin privileges and logon autostart option)"; GroupDescription: "Options:"; Flags: checkablealone
Name: "autostart"; Description: "Start at user logon (requires scheduled task)"; GroupDescription: "Options:"; Flags: unchecked; Check: IsScheduledTaskSelected

[Files]
Source: "dist\main.dist\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\{#MyAppExeName}"; DestDir: "{app}\app"; Flags: ignoreversion skipifsourcedoesntexist
Source: "dist\LetMeSleep-Updater.exe"; DestDir: "{app}"; DestName: "LetMeSleep-Updater.exe"; Flags: ignoreversion skipifsourcedoesntexist
Source: "dist\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"" --no-update"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"" --no-update"; Tasks: desktopicon

[Run]
; Install scheduled task with autostart if both selected
Filename: "{app}\app\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\app\{#MyAppExeName}'))
Filename: "{app}\main.dist\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\main.dist\{#MyAppExeName}'))
Filename: "{app}\main\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\main\{#MyAppExeName}'))
; Install scheduled task without autostart if only task selected
Filename: "{app}\app\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\app\{#MyAppExeName}'))
Filename: "{app}\main.dist\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\main.dist\{#MyAppExeName}'))
Filename: "{app}\main\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\main\{#MyAppExeName}'))
; Launch updater after install (it launches app)
Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"""; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove scheduled task on uninstall (if it exists)
Filename: "schtasks"; Parameters: "/Delete /TN ""LetMeSleep"" /F"; Flags: runhidden; RunOnceId: "RemoveTask"

[UninstallDelete]
Type: files; Name: "{app}\LetMeSleep-Updater.log"
Type: dirifempty; Name: "{app}"

[Code]
function IsScheduledTaskSelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask');
end;

function IsTaskOnlySelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask') and not WizardIsTaskSelected('autostart');
end;

function IsAutostartSelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask') and WizardIsTaskSelected('autostart');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Kill running instance before uninstall
    Exec('taskkill', '/F /IM LetMeSleep.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
