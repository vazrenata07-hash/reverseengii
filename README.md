# Mint Browser V12

[**Baixar Mint-Browser-v12-Refeito.apk**](Mint-Browser-v12-Refeito.apk) — clique em **Download raw file**. APK único, sem ZIP.

## Foco: filtro de elementos

A proteção anterior podia alcançar os controles `fast*` sem alcançar a janela principal montada em outra raiz do DOM. Esta versão dá prioridade à cena completa quando os componentes informados pelo usuário coexistem com um fundo escurecido de tamanho de tela, inclusive com classe gerada e início de animação em opacidade zero. Durante essa cena, libera os bloqueios próprios e aguarda o fechamento; depois retoma o filtro. Não escreve nos estilos do site nem aciona o botão de fechar.

As referências exatas e suas partes estáveis continuam protegidas: `_fastBtn_`, `_fastBackground_`, `_fastImg_`, `_closeIcon_3tzh2_`. CAPTCHA e formulários mantêm suas exceções. A proteção não considera o body inteiro um componente apenas por uma referência estática estar diretamente nele.

Testes passaram para controles, fundo e cartão como três raízes separadas, fundo com classe gerada, início de fade-in, restauração do cartão e retomada do bloqueio após fechar. São testes de DOM; a janela real ainda requer validação no aparelho.

## Limpeza no menu solicitado

Removido o botão sobre a página. No menu de **três pontos**, a ação que era **Localizar na página** passa a ser **Limpar dados**. O evento do item `action_menu_find_in_page` foi trocado para abrir a limpeza. O processo auxiliar apaga os dados e o cache e depois reabre o aplicativo.

## Mantido

Base: APK `mint-browser-3.9.3-direto (2).apk` enviado pelo usuário, com código adicional próprio da reconstrução. Código inicial de redirecionamento; usuário de 15 caracteres em `/register`; senha e confirmação `danill0`; um único motor cosmético no domínio afetado. O código adicional atual está em [src-v12](src-v12).

Compilação Android, geração do DEX, integridade, alinhamento e assinatura v1/v2/v3 verificados. A posição/ação do menu foi verificada nos recursos e no encaminhamento do evento; não houve execução Android neste ambiente.

SHA-256: `6a8ada07ace64cb7480dff38858b916862e7ed3476d95612b490ad2f70e27753`.
