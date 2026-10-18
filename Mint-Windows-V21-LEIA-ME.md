# Mint Windows V21

Executáveis para Windows 10/11 de 64 bits, baseados em Microsoft Edge WebView2. O .NET está incluído. O WebView2 Runtime precisa estar instalado: https://developer.microsoft.com/microsoft-edge/webview2/ . O aplicativo abre a página oficial se o runtime estiver ausente.

Abra o executável da senha desejada: danill0 ou 87654321. Na primeira execução, informe 0 ou o código de indicação. Cada variante mantém seus próprios dados. Os dados do APK Android não são importados.

## Portado da V21

- Filtros específicos de anúncios e exceções para CAPTCHA, recompensas, envelopes e caixas.
- Usuário aleatório de 15 caracteres ao entrar em /register e senha de login da variante.
- PIN 232691 nos campos de saque, incluindo confirmação, conforme os seletores existentes da V21.
- Contador acumulado do JDB Mines 9014, persistente em SQLite nativo do Windows. Não estima apostas por mudanças do saldo.
- Histórico das últimas 10 rodadas reveladas, com botão para mostrar/ocultar números nas casas. Nenhuma escolha automática de casas ou controle do autoplay.
- Abas, navegação, downloads, menu de três pontos, editor de user agent e ferramentas de desenvolvedor.
- Limpar dados e reiniciar fecha o aplicativo, aguarda a liberação do perfil e exclui cookies, armazenamento dos sites, cache, configurações e contador. Downloads salvos pelo usuário fora do perfil não são excluídos.
- Compatibilidade com certificados mantida conforme a configuração expressamente solicitada para o APK: o aplicativo permite certificados inválidos em suas páginas. O comportamento do motor não equivale à remoção de toda implementação TLS interna.

## Perfil Android

Perfil declarado: Samsung Galaxy A53 (SM-A536B), Android 13, ARM de 64 bits, navegador WebView móvel, toque com até cinco pontos e viewport móvel de 412 pixels CSS. A versão Chromium vem do WebView2 instalado. Identificação configurada via user agent, Client Hints do protocolo DevTools e propriedades JavaScript de navigator. Campos de alta entropia não conhecidos pelo adaptador retornam unknown quando solicitados.

O programa executa em Windows. Isso não é uma máquina virtual Android e não garante que um site deixe de identificar diferenças por GPU, fontes, codecs, temporização ou outras APIs. Campos nativos que o WebView2 não permite alterar não podem ser garantidos como unknown.

## Armazenamento

%LOCALAPPDATA%\MintBrowserWindows\v21-danill0\
%LOCALAPPDATA%\MintBrowserWindows\v21-87654321\

O histórico permanece no armazenamento local do frame do jogo. O contador usa mint_wager_counter.db e uma transação por aposta confirmada, com gravação fora da interface. O suporte ao contador/histórico continua restrito ao JDB Mines 9014 capturado em brteachcor.com; mudanças no site ou no jogo podem exigir atualização.

## Entrega

Compilado em Linux para Windows x64. Testes funcionais e de desempenho no Windows não executados por preferência do usuário. Não há certificado comercial de assinatura de código Windows; a assinatura Android não se aplica ao executável. A integridade da entrega é registrada por SHA-256.

Os scripts da V21 foram reaproveitados; as funções Android foram reimplementadas em C# / WinForms / WebView2. Não é uma conversão da interface proprietária completa do Mint nem uma reprodução de todos os recursos internos do Android.
