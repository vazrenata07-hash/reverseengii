# Mint Portable V25 — danill0

Correção da ponte do Mint para a detecção APP-Android(Vest) da 888. Windows 10/11 x64, .NET incluído, Microsoft Edge WebView2 Runtime necessário.

## O que mudou

A V25 expõe `window.jsBridge` com os seis métodos de adblock efetivamente presentes no APK Mint, encaminhados à implementação C# via COM. O objeto público é extensível para o lobby registrar e remover `onWebviewEvents`. A cópia interna `__mintAdblockBridge` permanece congelada para manter o filtro independente de alterações que o site faça no objeto público.

Na V23, `jsBridge` era congelado e o registro de callback encontrado no código do site lança TypeError nesse objeto. Na V24, a ponte ficou somente com o nome interno; a página voltou a abrir, mas deixou de satisfazer a detecção de aplicativo. A V25 restaura o nome original e permite o callback. A inicialização/reinicialização do listener nativo passa a `true`, igual ao APK Android.

O restante do JavaScript funcional, incluindo filtro, senha danill0, PIN, contador e histórico, mantém o código da V24. User agent e largura da janela continuam iguais.

## Evidência do site

As fontes do lobby enviadas pelo usuário contêm o detector `W6`/`re.package`, que aceita a presença de `jsBridge` e considera Vest quando não há configuração SpeedPack. Os métodos `Ug`/`Gg` e `WI` geram, para Android + Vest, `x-device: 2-4` e `deviceOsType: 2`. Esses valores são calculados pelo próprio código do site. A V25 não precisa mudar a implementação das requisições.

O mesmo código define `os_type: 6`, `clientType: 5` e `platformType: "1001"` nesse fluxo; esses campos não devem ser trocados por valores presumidos.

Origem: `assets/theme-0/commonChunk.EZ6HNUYg.js`, captura de 18/10/2026. SHA-256: `a4b6a7fb2870cbb6b1f89ebf2661ba7436b4e3a92250973910085749cc18f87f`. O fixture de teste contém somente os trechos usados, com offsets e hashes.

## Usar e verificar

1. Feche a versão anterior.
2. Execute `Mint-Browser-Windows-v25-Portable-danill0.exe` na mesma pasta de `MintData`.
3. Saia da conta e entre novamente na V25 para gerar um registro de login com a ponte atualizada.
4. Confira Cliente em Dispositivo atual. O objetivo é APP-Android(Vest).

Não é necessário apagar `MintData`. Um registro de sessão existente pode continuar exibindo o cliente H5 anterior até um novo login.

## Validação e limite

Build Release Windows x64 concluído. Oito verificações passaram com as funções exatas de classificação, payload de login e callback extraídas da captura. O teste reproduz o TypeError da ponte congelada quando o registro de callback é executado; confirma classificação H5 na V24 e Vest/Android App na V25; verifica registro/limpeza/reinstalação do callback, encaminhamento nativo simulado, limites de domínio/frame, preservação de ponte existente e compilação do script gerado.

Executar: `node src-windows-v25/tests/verify-v25.cjs`.

O parser de user agent e os métodos COM usam fixtures nesses testes. O factory de eventos importado do vendor não está na captura; o teste chama diretamente o registro de callback real. Não houve execução completa do lobby, do WebView2 no Windows ou login no servidor neste ambiente. O registro final APP-Android(Vest) precisa ser confirmado após novo login no computador do usuário.

SHA-256 do EXE: `26931693b37db8dfaccb7b9e042c7a201e715d69fa7411f8cd0042362809c765`.
