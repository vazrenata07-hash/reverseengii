V21: histórico passivo de bombas das últimas 10 rodadas concluídas no JDB Mines 9014. Preserva contador e alterações V20. Botão exclusivo do jogo mostra/oculta números em cada casa, usando a mesma ordem dos cards Cocos. Nenhuma seleção, recomendação, clique no jogo ou controle do autoplay.

Observa a promise original de cashoutRequest, cuja resposta final gameResult.map contém o mapa revelado: OpenMine=4 e CoveredMine=7. Deduplica por gameSeq, mantém no máximo 10 mapas, persiste em localStorage do jogo. Limpar dados apaga o histórico. Não importa rodadas anteriores à instalação.

Cria os Labels só ao abrir o histórico; usa atlas de caracteres; ao ocultar, desativa todos os nós de números. Atualiza apenas ao receber rodada concluída, sem polling adicional nem animações. Botão HTML estático no topo direito do frame do jogo. Mesma captura/provedor/versão específica da V20.

Compilação e assinatura executadas. Testes funcionais e regressão pulados por solicitação do usuário; aparência e comportamento no aparelho ainda dependem da verificação do usuário.
