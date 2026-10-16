# Mint Browser V7

Versão atual: **V7**. Abra [Mint-Browser-v7-download.zip](Mint-Browser-v7-download.zip), clique no ícone de download (**Download raw file**) e extraia o ZIP para obter o APK.

## Correções da V7

- O detector não executa cliques automáticos em botões de fechar.
- Nas rotas de cadastro, login e verificação, o removedor cosmético fica suspenso para preservar o CAPTCHA, inclusive sua janela inicial ainda sem conteúdo. O preenchimento de usuário e senha continua ativo.
- Não aplica o detector dentro de iframes; preserva janelas com iframe, canvas, slider e identificadores ou textos de CAPTCHA/verificação.
- Exceções para as recompensas indicadas pelo usuário: bônus de login diário, bônus de aposta efetivo, baú/presente, saco e envelope. Reconhecimento por textos como ABRIR/RESGATAR/COLETAR e identificadores ou imagens com nomes de recompensa, sem regras globais que ocultem classes compartilhadas.
- Se uma janela ocultada receber posteriormente conteúdo identificável de CAPTCHA ou recompensa, ela é restaurada, sem ter seu botão de fechar acionado.
- Mantidos o usuário aleatório de 9 caracteres em `/register`, senha e confirmação `danill0`, e a remoção dos filtros antigos por classe e API.

Testes de lógica/DOM, recompilação, alinhamento e assinatura passaram. As exceções precisam de validação visual no site real pelo usuário; não há reconhecimento visual das imagens em tempo real.

SHA-256 do APK V7: `e5a7b55d5658bd335473f9fc258f68a1b9e1281dcc32f04602e4db3f8cba96dd`.

V5 e V6 permanecem apenas como versões anteriores.
