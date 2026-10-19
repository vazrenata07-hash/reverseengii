# Diagnóstico passivo do carregamento do SDK de cadastro

Este pacote é para o Mint V25 no Windows, onde o mesmo aviso de cadastro também foi confirmado. Observa o carregamento do SDK e erros técnicos; não cria contas e não modifica as validações do site.

## Executar

1. Feche todas as janelas do Mint.
2. Coloque os dois scripts na mesma pasta de `Mint-Browser-Windows-v25-Portable-danill0.exe`.
3. Execute `diagnosticar-sdk-cadastro.bat`.
4. Quando a captura começar, abra somente o formulário de cadastro. Aguarde 60 segundos sem enviar o formulário.
5. Feche o Mint e envie o TXT gerado na mesma pasta.

O relatório registra estados booleanos do navegador/SDK, status e duração dos recursos permitidos, códigos de erro de rede e categorias de exceção. Não grava credenciais, identificadores de dispositivo, tokens, cookies, armazenamento, corpos de requisição/resposta ou cabeçalhos. Nenhum relatório é enviado automaticamente.

## Como interpretar

O código do lobby separa a classificação APP-Android(Vest) da validação de cadastro. No modo Vest, o fluxo usa o SDK JavaScript. A mensagem genérica não demonstra que a ponte da V25 esteja com defeito.

Uma falha observada de carregamento ou recurso do navegador pode justificar uma correção de compatibilidade. A presença do SDK, sozinha, não prova que toda a inicialização ou validação terminou com sucesso. O diagnóstico não revela as regras de risco e não garante identificar a causa de uma recusa do servidor.

Se a plataforma continuar recusando o cadastro, encaminhe a referência exibida no aviso ao suporte da 888 para revisão. Para Android, use uma instalação e um WebView oficialmente suportados.

## Validação

Passaram verificação de sintaxe e testes de seleção de recursos, exclusão de dados sensíveis, estados booleanos e transporte CDP. Um teste com Chromium real e conteúdo sintético local verificou recursos HTTP 200/404, exceção sanitizada, ausência de chamadas ao SDK e ausência de recarga. A execução real no Windows/888 ainda precisa ser feita no computador do usuário.
