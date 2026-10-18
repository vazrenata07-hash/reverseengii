# Classificação APP-Android(Vest): objetivo pendente

O usuário confirmou APP-Android(Vest) no Mint APK em Android e H5 no Chrome em Android/Windows. A V24 deixou de travar e continua H5. Esse resultado não satisfaz o objetivo principal.

A análise estática do APK V21 encontrou `jsBridge` com exatamente seis métodos de adblock. O Android inicia `getAddDomListener()` como `true`; a ponte Windows inicia e reinicia como `false`. `getElemhideSelectors()` devolve string JSON nas duas plataformas. Não há evidência de que o estado inicial seja consultado pelo lobby.

O Mint Android também publica `mint`, `readmode`, `adChecker`, `downloader`, `nightModeJsCallback` e `miui`. `mint.getVersionCode()` devolve 20220322 e `mint.getVersionName()` devolve 3.9.3. `miui.getDeviceInfo()` depende de uma lista/regex de domínios permitidos, com domínios Xiaomi por padrão. Não foi encontrada uma API específica da 888 nesse APK.

A V23 criava um wrapper congelado em `window.jsBridge`; a V24 usa `window.__mintAdblockBridge`. A regra do site que produz os metadados do cliente e a chamada exata que travava a V23 ainda não foram capturadas. Não se pode afirmar que faltava a API inteira do app da 888 ou que `Object.freeze` causou a falha.

O coletor lê os scripts já carregados com o Debugger do WebView2 e salva fontes externas limitadas, trechos inline, indicadores de detecção e erros. Não injeta marcadores de aplicativo ou respostas nativas. O próximo passo depende do ZIP produzido no computador do usuário: localizar a classificação e comparar com o contrato real do Mint antes de propor outra versão.

## Correção do coletor v2

O ZIP retornado pelo usuário em 18/10/2026 continha somente um log: a coleta parou em `Runtime.enable`, sem fontes. O `GetResult()` de um `SendAsync()` concluído imediatamente emitia `VoidTaskResult` no pipeline do PowerShell, transformando o identificador retornado em um array. Assim a resposta CDP correta não era reconhecida. A v2 suprime esse resultado e exige um identificador inteiro.

A falha original foi reproduzida em uma conexão CDP com Chromium real local. A versão corrigida passou em inicialização Runtime/Log/Network/Page/Debugger, recarga, dez respostas sucessivas, extração de trechos e transferência integral de duas fontes, incluindo uma de 228 KB. Esse teste usa conteúdo sintético local; ainda é necessário obter o código da 888 no computador do usuário.

## Capturas retornadas e correção da seleção v3

As duas coletas retornadas, incluindo uma sessão logada, registram a mesma implementação real: `LOBBY_UTILS.isAppEnv()` verifica `WgPackage`, `jsBridge`, `PlatNative`, `Android`, `uni` ou parâmetros de URL; `isVestEnv()` é `isAppEnv() && !getSpeedPackConfig()`. A V24 tem somente `__mintAdblockBridge`; `jsBridge` está ausente. Isso confirma a diferença no detector inicial, sem provar a classificação que será enviada ao servidor após corrigir a ponte.

O coletor selecionava até 30 fontes por tamanho crescente. As capturas tinham 58/117 candidatas; os módulos centrais foram excluídos. Faltam `assets/theme-0/commonChunk.EZ6HNUYg.js` e `assets/theme-0/0_EntryLoginRegisterChunk.D7_g9aJ6.js`. A implementação da ponte e os metadados compartilhados são importados deles pelos módulos capturados. O arquivo `register.impl` capturado trata de webpush.

A v3 prioriza commonChunk e EntryLoginRegisterChunk, deduplica contextos por host/caminho e aumenta o limite por fonte para 8 MiB. O teste de regressão cria mais de 50 auxiliares, contextos duplicados e fontes grandes para verificar que o núcleo é coletado primeiro e que os limites e a exclusão de documentos completos continuam válidos. O navegador e seus identificadores não foram alterados nesta etapa.
