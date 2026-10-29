# Somente leitura. O caminho e os descritores transitam em memória, nunca em logs.
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$stage='entrada'
try {
    $request=[Console]::In.ReadToEnd() | ConvertFrom-Json
    $stage='compilacao'
    Add-Type -Path $env:CONVERSOR_ACL_PROBE_CS -ErrorAction Stop
    $key=[Convert]::FromBase64String($request.chave)
    $named=[Convert]::FromBase64String($request.named)
    $file=[Convert]::FromBase64String($request.file)
    $all=[Convert]::FromBase64String($request.named_all)
    $meta=[Collections.Generic.Dictionary[string,string]]::new()
    foreach($property in $request.meta.PSObject.Properties) { $meta[$property.Name]=[string]$property.Value }
    $stage='leitura'
    $readAcl=[System.Func[System.Security.AccessControl.FileSystemSecurity]] { Get-Acl -LiteralPath $env:CONVERSOR_ACL_DIAG_PATH -ErrorAction Stop }
    $result=[ConversorAclProbe]::Run($env:CONVERSOR_ACL_DIAG_PATH,$key,$named,$file,$all,$meta,$readAcl)
    $result | ConvertTo-Json -Compress -Depth 14
} catch {
    # Nunca devolver mensagens de exceção: podem conter caminho, SDDL ou contas.
    @{erro='PROBE_WINDOWS_NAO_COMPROVADO';etapa=$stage} | ConvertTo-Json -Compress
    exit 2
}
