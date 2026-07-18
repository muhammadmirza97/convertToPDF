Option Explicit

Dim fileSystem, shell, projectFolder, pythonWindow, appScript
Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

projectFolder = fileSystem.GetParentFolderName(WScript.ScriptFullName)
pythonWindow = projectFolder & "\.venv\Scripts\pythonw.exe"
appScript = projectFolder & "\run_app.py"

If Not fileSystem.FileExists(pythonWindow) Then
    MsgBox "The app environment is missing. Complete the Windows Setup steps in README.md first.", vbExclamation, "Local PDF Converter"
    WScript.Quit 1
End If

shell.Run Chr(34) & pythonWindow & Chr(34) & " " & Chr(34) & appScript & Chr(34), 0, False
