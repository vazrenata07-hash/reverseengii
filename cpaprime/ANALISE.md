# CPAprime — tentativa de conversão para portátil

Status: conversão não concluída. Nenhuma versão portátil foi gerada ou validada.

## Arquivo analisado

- Nome: CPAprime_Installer.exe
- Tamanho: 3.750.139 bytes
- SHA-256: d71729f2febabdf76b4580d9bf27d86727b09faa191f9521d615bc9397dfded6
- Formato: executável Windows PE32, Intel i386.
- Identificação estática: Inno Setup Setup Data (6.7.0).

## Procedimento e resultado

O instalador não foi executado. Foi feita identificação estática e tentativa de listagem com innoextract 1.9, sem instalar o aplicativo.

A ferramenta retornou:

```
Warning: Unexpected setup loader revision: 2
Warning: Setup loader checksum mismatch!
Could not determine setup data version!
```

Essas mensagens não comprovam corrupção ou presença de malware: a versão da ferramenta não conseguiu interpretar o instalador. Nenhum arquivo do aplicativo foi extraído.

## Próximo passo

Usar um extrator compatível com Inno Setup 6.7 e conferir dependências, ações do instalador, serviços e uso do Registro antes de afirmar que o programa funciona sem instalação. Validar a execução em ambiente Windows isolado.

Tornar um aplicativo portátil não comprova sua segurança nem impede alterações no computador quando ele for executado.

Este commit contém apenas o relatório. O instalador original e um executável portátil não estão incluídos.
