# Mint Portable V26 — teste com perfil nativo

Esta versão compara o cadastro com o perfil real do Microsoft Edge WebView2 no Windows, mantendo a ponte nativa da V25. Não afirma que o perfil anterior era a causa do erro.

## Alterações

- Removidos o user-agent Android e os overrides de `navigator.platform`, `vendor`, `maxTouchPoints`, `userAgentData` e `oscpu`.
- Removidas as chamadas de emulação de user-agent, plataforma, idioma e toque. O WebView2 passa a informar seus próprios valores.
- Removido o menu de user-agent. O campo antigo em `MintData/settings.json` é ignorado e não reaplica o perfil Android.
- Preservada, sem alteração, a ponte extensível `jsBridge` da V25, com os mesmos seis métodos nativos de bloqueio de anúncios.

O rótulo do cliente e os campos de sistema apresentados pela 888 são calculados pelo próprio site. A V26 não força esses campos nem altera requisições, respostas ou a validação de cadastro.

## Testar

1. Feche a V25 e abra `Mint-Browser-Windows-v26-Portable-danill0.exe` na mesma pasta. Ela usa o mesmo `MintData`; não é necessário limpar os dados.
2. Faça o teste manual normal de cadastro e observe se o aviso continua. O navegador não envia cadastros automaticamente.
3. Para comparar a tela de dispositivo, faça um novo login; registros anteriores podem continuar mostrando os dados antigos.

A interface do site pode mudar para o layout de computador, pois o perfil agora é o do Windows. A janela continua redimensionável.

## Validação e limites

A compilação é Windows x64, .NET 8 incluído; Microsoft Edge WebView2 Runtime continua necessário. Os testes verificam que o script preserva os valores e descritores originais de `navigator`, mantém os métodos e callbacks da ponte e respeita os limites de domínio e frame. Também comparam o restante do script com a V25.

O ambiente de desenvolvimento não executa WebView2/WinForms no Windows. A aprovação do cadastro e o rótulo exibido pela 888 precisam ser observados no computador do usuário.
