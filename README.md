# Mint Browser V6

Versão atual: **V6**. Abra [Mint-Browser-v6-download.zip](Mint-Browser-v6-download.zip), clique no ícone de download (**Download raw file**) e extraia o ZIP para obter o APK.

- Removidos os seletores cosméticos antigos por classe e os bloqueios fixos de API adicionados na edição anterior.
- O detector identifica contêineres sobrepostos com controle de fechar, sem usar a classe encontrada para bloquear outros elementos. Formulários e a estrutura principal da página são preservados pelo detector.
- Em `888pg.cc` e subdomínios, ao entrar em `/register` (inclusive por navegação interna e hash), gera um novo usuário aleatório de 9 caracteres alfanuméricos e preenche o campo combinado Celular/E-mail/Conta. Mantém o nome durante a mesma visita ao formulário.
- Senha e confirmação: `danill0`.

Testes de lógica/DOM, recompilação, alinhamento e assinatura passaram. Resultado visual e comportamento no site real dependem do teste no aparelho; não foram verificados em Android neste ambiente.

SHA-256 do APK V6: `efe0ddbed69c3578217d7613db633a0587d5f7fefff76379b92714922982a71d`.

A V5 permanece disponível apenas como versão anterior.
