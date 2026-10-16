# Mint V15

Corrige a descoberta do componente de recompensa quando há controles duplicados para layouts desktop/mobile. A presença de múltiplos X não interrompe mais a proteção do ancestral da recompensa. Caso uma camada decorativa intercepte um toque real dentro do retângulo do X de uma recompensa, encaminha o clique ao controle original uma vez. Não remove manualmente o DOM da recompensa nem altera seu estado; cliques já destinados ao X seguem normalmente. CAPTCHA e ABRIR permanecem fora do encaminhamento automático.

Validação: regressão reproduzida na V14 com controles responsivos duplicados. Teste Chromium com toque de touchscreen e camada externa interceptadora passou após a correção. Testes anteriores de anúncios/recompensas/CAPTCHA/cadastro passaram. APK compilado, alinhado e assinaturas v1/v2/v3 verificadas. Sem teste em aparelho Android ou acesso ao DOM real do site; testes usam fixtures locais.
