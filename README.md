# Mint Browser V11 — reconstrução sobre o APK enviado

## Download único, sem ZIP

[**Mint-Browser-v11-Refeito.apk**](Mint-Browser-v11-Refeito.apk)

Abra o arquivo e clique em **Download raw file** (⬇).

## Base e código

Base: `mint-browser-3.9.3-direto (2).apk`, enviada pelo usuário. O navegador original foi mantido como base; as novas funções foram escritas novamente, em código próprio. Não foram incluídas classes ou scripts dos filtros V4–V10. Os seletores informados pelo usuário servem como referências de proteção.

O código adicional está em [src-v11](src-v11):

- `Bootstrap.java`: tela inicial de código e botão nativo de limpeza.
- `ResetActivity.java`: encerra o navegador, limpa em um processo separado e abre o aplicativo novamente.
- `DataWiper.java`: exclusão das pastas privadas, sem seguir links e preservando a biblioteca do aplicativo.
- `PageScripts.java`: carregamento do script e instalação antecipada pelo suporte do WebView, com fallback por eventos de página.
- `mint-rebuilt.js`: novo filtro de elementos e novo preenchimento de cadastro.

## Funções desta versão

- Código na abertura: `0` abre `https://888pg.cc/`; código numérico com pelo menos 7 dígitos abre `/home/register?id=CODIGO`. A tela reaparece após limpar os dados.
- Botão **Limpar dados ↻**, acima da barra inferior: apaga perfil, histórico/configurações locais, bancos de dados, armazenamento WebView/cookies e cache, encerra os processos do navegador e reabre. Downloads públicos do aparelho não são apagados. Se houver falha de exclusão, informa limpeza incompleta.
- Usuário alfanumérico aleatório de **15 caracteres** em cada entrada em `/register`, no domínio `888pg.cc` e subdomínios.
- Senha e confirmação: **`danill0`**. Apenas um APK.
- Novo filtro: primeiro identifica componentes protegidos; depois planeja o bloqueio dos flutuantes com controle de fechar. Oculta apenas por atributo CSS, sem escrever nos estilos inline nem clicar em fechar.
- Exceções para os componentes `_fastBtn_`, `_fastBackground_`, `_fastImg_` e o `_closeIcon_3tzh2_` informado; CAPTCHA, formulários e recompensas também são preservados.
- Nesse domínio, a ocultação cosmética nativa não injeta um segundo filtro concorrente. Fora desse domínio, o comportamento original dos filtros nativos foi preservado.

Foram implementados os pedidos acessíveis nesta conversa. Esta implementação não pressupõe acesso a outros chats do Work.

## Validação

Passaram testes de DOM para cadastro, renovação do usuário, domínio/subdomínios, 15 caracteres, senhas, proteção do componente exato e seus ancestrais, conteúdo tardio, CAPTCHA e ausência de cliques/alteração de estilos. Testes de arquivos verificaram remoção do perfil/cache, preservação da biblioteca e de destinos externos de links, incluindo links quebrados e circulares. Java compilado para Android, DEX gerado com API mínima 19, APK recompilado, alinhado e assinatura v1/v2/v3 verificada.

Não houve execução em aparelho/emulador Android neste ambiente. A interação visual, o reinício e o comportamento no site real ainda precisam de validação no aparelho.

SHA-256: `c87cc28410c3a58d69a454330b22eab02d261c4af618e4c2ced59a28848372ce`.

Versões antigas ficam apenas como histórico; esta versão parte do novo APK enviado.
