# Metadados da abertura do CAPTCHA

1. Abra o Mint no Windows, pressione F12 e entre em **Rede/Network**.
2. Marque **Preservar log/Preserve log** e mantenha **Desabilitar cache/Disable cache desmarcado**, para registrar a condição normal. Use o filtro **Tudo/All** e limpe a lista de requisições.
3. Reproduza uma única abertura real do CAPTCHA. Inicie a captura antes do clique que dispara o desafio e aguarde aparecer. Se o desafio só surgir depois do envio do formulário, use uma tentativa manual normal que você já faria. O sanitizador não envia formulários nem executa ações no site.
4. Anote aproximadamente quanto tempo levou do clique até aparecer. Não é necessário resolver o CAPTCHA para analisar sua abertura.
5. Exporte o registro como HAR, de preferência a opção sanitizada do DevTools. Dependendo da versão, fica no botão Exportar HAR ou no menu ao clicar com o botão direito na lista. O HAR bruto pode conter dados sensíveis mesmo quando o DevTools o chama de sanitizado.
6. Execute **extrair-metadados.bat** e escolha esse HAR. Também pode arrastar o HAR para o BAT. Envie somente o novo arquivo `mint-captcha-rede-...json`.

O script lê o HAR localmente e gera uma lista de URLs sem query strings, fragmentos ou login/senha na autoridade da URL, método, status, tempos, tamanhos, tipo e origem da requisição. Não copia cabeçalhos, cookies, corpos de formulários ou conteúdo de respostas. Mantém domínios e caminhos para identificar dependências; identificadores longos em segmentos são mascarados, mas os caminhos ainda podem conter dados pessoais ou tokens não reconhecidos. Revise o JSON e remova essas informações antes de compartilhar. Não envia nada pela rede.

A captura Windows ajuda a analisar o fluxo de rede comum; não reproduz os tempos de renderização ou as condições do aparelho Android. Caso já tenha um HAR obtido por inspeção remota do Android, o mesmo sanitizador pode ser usado.

Nenhum teste ou benchmark foi executado nesta entrega.
