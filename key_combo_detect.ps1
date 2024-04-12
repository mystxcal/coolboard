$Signature = @'
    [DllImport("user32.dll", CharSet=CharSet.Auto, ExactSpelling=true)] 
    public static extern short GetAsyncKeyState(int virtualKeyCode); 
'@
Add-Type -MemberDefinition $Signature -Name Keyboard -Namespace PsOneApi

$key = '0x10' ## Shift
$key2 = '0x12' ## Alt

do
{
    If([bool]([PsOneApi.Keyboard]::GetAsyncKeyState($key) -eq -32767) -and 
       [bool]([PsOneApi.Keyboard]::GetAsyncKeyState($key2) -eq -32767))
    { 
        Write-Host "show"
    }
    else
    {
        Write-Host "hide"
    }
    Start-Sleep -Milliseconds 100
} while($true)
