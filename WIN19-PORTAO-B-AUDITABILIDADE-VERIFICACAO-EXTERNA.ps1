# VERIFICADOR EXTERNO PROPOSTO. NAO EXECUTADO. Nao invoca scripts nem extrai ZIP.
# Conferir seu proprio SHA externamente antes de usa-lo; nao ha autoautenticacao.
param(
    [Parameter(Mandatory=$true)][string]$Zip,
    [string]$Preparacao
)
$ErrorActionPreference = 'Stop'
$ZipEsperado = '6900cb660374d730708669e20e900cf2a2e52a73774108a873844014532d7675'
$EntradaEsperada = 'd42a5097ea8f2693f226dc77a9abaa6fc243e5346bac79dbb6a4efc9fa3eede4'
$ManifestoEsperado = '24f81e91ef1259b8f100d01294424f0c31a199d9c30a772122aa22ff571831ff'
function Conferir-Arquivo([string]$Path, [string]$Esperado) {
    if (-not [IO.Path]::IsPathRooted($Path)) { throw 'CAMINHO_DEVE_SER_ABSOLUTO' }
    $Atual = [IO.Path]::GetFullPath($Path)
    while ($Atual) {
        $Item = Get-Item -LiteralPath $Atual -Force
        if (($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'REPARSE_RECUSADO' }
        $Pai = [IO.Path]::GetDirectoryName($Atual)
        if ($Pai -eq $Atual) { break }
        $Atual = $Pai
    }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Esperado) {
        throw 'HASH_EXTERNO_DIVERGENTE_PRESERVAR'
    }
}
# Primeira chamada, ANTES da extracao, pode informar somente -Zip.
Conferir-Arquivo $Zip $ZipEsperado
if (-not $Preparacao) {
    Write-Output 'ZIP_CONFERIDO; NAO_EXTRAI; NAO_AUTORIZA_EXECUCAO'
    return
}
# Segunda chamada, apos extracao manual em pasta NOVA e ANTES da invocacao.
$LocalWIN19 = [Environment]::GetFolderPath([System.Environment+SpecialFolder]::LocalApplicationData)
$Destino = Join-Path $LocalWIN19 'WIN19-Portao-B-Ajustes\preparacao'
if (-not [string]::Equals([IO.Path]::GetFullPath($Preparacao), $Destino, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'DESTINO_DIFERENTE_DO_REVISADO'
}
Conferir-Arquivo (Join-Path $Preparacao 'COMANDO_PORTAO_B_NAO_EXECUTADO.ps1') $EntradaEsperada
Conferir-Arquivo (Join-Path $Preparacao 'MANIFESTO_PORTAO_B_SHA256.json') $ManifestoEsperado
Write-Output 'ZIP_ENTRADA_MANIFESTO_CONFERIDOS; ESCOPO_MATERIAIS_A_CONFERIR_PELA_ENTRADA; SEM_EXECUCAO'
