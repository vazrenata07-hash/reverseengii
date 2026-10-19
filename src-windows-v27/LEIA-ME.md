# Mint Portable V27 — modo dispositivo

Use o botão **Dispositivo** na barra superior ou **⋮ → Modo dispositivo**. Escolha um dos 25 perfis de visualização Android, a orientação e o toque; clique em **Aplicar**. Para voltar ao modo normal, escolha **Windows — tamanho da janela**.

O modo ajusta dimensões CSS, densidade de pixels, orientação e entrada por toque. A prévia se ajusta ao espaço disponível. A seleção vale para as abas abertas e novas e fica salva em `MintData/settings.json`. Limpar os dados restaura o modo normal da janela.

O sistema e o navegador informados aos sites continuam sendo os reais do WebView2 no Windows. Este painel não escolhe nem executa versões do Android e não altera user-agent, Client Hints, identificadores de dispositivo ou os getters de identificação de `navigator`. Alguns sites podem escolher o layout pelo user-agent mesmo com uma área de exibição móvel.

Há 17 perfis extraídos do catálogo público do Chrome DevTools e 8 aproximações marcadas com **(aprox.)**. Os nomes identificam referências de tela; não transformam o computador no aparelho indicado. Dobráveis usam somente a tela externa, sem simulação de dobradiça ou abertura.

Ponte nativa, script e demais recursos da V26 foram preservados. O EXE usa o mesmo `MintData`; feche a versão anterior antes de abrir esta. Não é necessário apagar os dados.

Compilação Windows x64 com .NET incluído; requer Microsoft Edge WebView2 Runtime. Nenhum teste foi executado nesta entrega, conforme solicitado pelo usuário.
