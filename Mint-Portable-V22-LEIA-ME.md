# Mint Portable V22 — danill0

Windows 10/11 de 64 bits. Abra o executável em uma pasta com permissão de escrita. Não requer instalador; o .NET está incluído e o WebView2 Runtime continua sendo necessário. Perfil, cookies, cache, configurações, contador e histórico ficam na pasta MintData junto ao EXE. Para mover o programa mantendo os dados, mova o EXE e MintData juntos. A versão V21 em AppData não é importada nem apagada automaticamente.

## Alterações desta versão

- Removida a emulação fixa de 412 pixels: o WebView2 usa a largura e a altura reais da área da janela, inclusive ao redimensionar.
- Identificação padrão compatível com Android Browser 4.0 / Android 13 / Samsung SM-A536B. Removidos os tokens Chrome e wv e os Client Hints de Chrome WebView. Não injeta uma versão de sistema via UA-CH.
- Uma única variante, senha de login danill0; os demais scripts de filtros, preenchimento, PIN, contador e histórico foram preservados.
- Limpar dados e reiniciar apaga somente MintData desta cópia portable. Downloads externos e dados da V21 anterior não são apagados.

## Identificação e limites

A comparação local com UAParser 2.0.6, solicitada pelo usuário, classificou o identificador V21 como Chrome WebView 155 e o V22 como Android Browser 4.0, Android 13, Samsung SM-A536B. Isso não é uma confirmação da classificação feita pelo servidor do site.

APP-Android(Vest) é uma categoria do site distinta do nome do navegador. Não foi localizada, nas fontes capturadas disponíveis, a regra exata que atribui essa categoria. Pode depender de informações além do user agent. Esta versão não falsifica o texto da tela de informações, não altera dados de login para impor uma categoria e não inventa uma integração nativa Android.

O motor continua sendo Microsoft WebView2 no Windows. É um perfil de identificação móvel, não um emulador Android. Informações armazenadas pelo site em uma sessão antiga podem continuar com a classificação antiga até um novo login.

## Verificações

Compilação Windows x64 concluída; comparação local dos identificadores realizada por solicitação do usuário. Testes funcionais no Windows/site e baterias de regressão não executados. O executável não possui assinatura comercial de código Windows.
