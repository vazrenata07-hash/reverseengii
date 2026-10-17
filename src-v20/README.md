V20: contador persistente para JDB Mines, jogo 9014, integrado ao InfoPanel do próprio canvas Cocos. Base V19 preservada.

O HAR mostrou bar.createGame como preparação, e bar.spinResponse com betResult.gameSeq como confirmação da primeira aposta da rodada. checkRequest fornece a aposta em reais; armazenamento em milésimos, uma entrada por gameSeq, transação SQLite, total independente de saldo/ganhos. 19 confirmações de R$1 identificadas na captura. Apostas passadas não são importadas. Captura e credenciais não incluídas no repositório.

A integração observa a promise original de MinesServerProxy.checkRequest sem modificar os pedidos, os retornos nem o autoplay. Usa um Label Cocos ao lado de balance no InfoPanel, com reserva de espaço para gameSeq. Nenhuma camada HTML flutuante. Bridge Android só oferece consulta/registro do contador e só é habilitada em WebViews com página principal 888pg.cc ou subdomínio. Ledger e total persistem em mint_wager_counter.db, apagado pela ação Limpar dados.

Suporte específico ao jogo Mines capturado, não universal para todos os jogos. Requer injeção em subframes por DOCUMENT_START_SCRIPT do Android WebView. Compilação e assinatura realizadas; testes funcionais/regressão não executados conforme preferência do usuário. Validação visual no aparelho pendente.
