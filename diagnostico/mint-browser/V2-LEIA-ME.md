# Mint Diagnóstico V2

Versão experimental instrumentada a partir do Mint 3.9.3 fornecido pelo usuário. Não é uma versão oficial da Xiaomi. O funcionamento de navegação, DNS e VPN do navegador não foi alterado. As sondas avançadas requerem Android 7/API 24 ou superior.

## Uso

1. Instale `Mint-Diagnostico-V2.apk`. Usa o mesmo certificado de teste da V1, portanto normalmente pode ser instalada como atualização dessa versão modificada. A versão oficial tem outra assinatura.
2. Toque em **Ativar diagnóstico**, confirme o domínio ou altere para o site que deseja testar. Aceita domínio ou URL HTTP/HTTPS e testa apenas o domínio, nas portas 80 e 443.
3. Reproduza o problema **durante a gravação**. Aguarde até 45 segundos para as sondas terminarem. O navegador continua utilizável.
4. Mantenha **Desativar** pressionado para consultar o relatório e as conclusões. Um toque simples desativa e abre o seletor de destino para exportar o JSONL.
5. Ativar uma nova sessão limpa o log anterior da memória. Arquivos exportados não são apagados. Resultados de sondas antigas não entram na nova sessão.

## Evidências coletadas

- DNS do sistema Android: IPs retornados, erro e tempo. Este teste pode usar cache e DNS privado e não revela o servidor consultado internamente pelo Chromium.
- Consulta DNS explícita a cada servidor configurado na rede selecionada: tipos A e AAAA, servidor/IP, UDP/53, código RCODE (`NOERROR`, `NXDOMAIN`, `SERVFAIL`, `REFUSED` etc.), TTL, CNAME, IPs, tempo e pacote de resposta hexadecimal. Respostas truncadas acionam tentativa por TCP/53.
- Referências independentes por DNS sobre HTTPS: Google (`dns.google`, IP inicial 8.8.8.8) e Cloudflare (`cloudflare-dns.com`, IP inicial 1.1.1.1), com validação normal de certificado, hostname e SNI. Usar IP inicial evita depender do DNS do sistema para localizar essas referências. O domínio escolhido é enviado a esses dois serviços; cookies e páginas não são enviados.
- TCP separado para portas 80 e 443 em até dois IPv4 e dois IPv6 obtidos nos testes DNS. Registra origem do IP, rede selecionada, IP local, tempo e exceção.
- TLS com hostname/SNI original, cadeia de certificados validada, emissor, validade, SHA-256, versão TLS e cifra. Falhas preservam tipo e mensagem da exceção. A validação nunca é desativada.
- HTTP e HTTPS: `GET /` sintético, Host original, status, Server, Content-Type e origem do redirecionamento. Não envia cookies nem segue redirecionamentos e não captura o corpo da página. O transporte usa sockets próprios; não é uma reprodução integral das políticas de proxy/cleartext do WebView.
- WebView: erros de carregamento, HTTP e TLS, código Chromium reconhecível quando disponível, configurações e user-agent; rede/DNS privado/VPN reportados pelo Android e eventos genéricos de toque.

As sondas usam a rede vinculada ao processo, se existir, ou a rede ativa capturada no início. Não selecionam a rede física por trás da VPN. Mudanças de rede são sinalizadas no relatório. Se a VPN proibir sockets vinculados, a falha é registrada, sem tentar contorná-la.

## Conclusões e limites

O evento `DIAGNOSIS` contém as evidências e conclusões. Se o WebView informar falha DNS depois das sondas, `DIAGNOSIS_WEBVIEW_UPDATE` atualiza a comparação. Erros posteriores podem pertencer a outro instante de rede/cache.

O relatório distingue divergência entre DNS do sistema e DoH, NXDOMAIN divergente, conectividade IPv4/IPv6 diferente, certificado rejeitado e resposta HTTP 403/451. Nenhum desses sinais isolados é tratado como prova de censura ou de falha específica da operadora. HTTPS para a raiz responder não comprova funcionamento de login, JavaScript ou do caminho original.

Não intercepta os pacotes DNS internos reais do Chromium e não captura todo tráfego do aplicativo. DNS direto na porta 53 é uma sonda explícita, podendo diferir do caminho de DNS privado do navegador. Se os servidores DoH estiverem inacessíveis, o relatório registra essa limitação. Não há root, VPN embutida, interceptação de TLS ou instalação de CA.

A rodada tem prazo de 45 segundos; desativar antes registra resultado incompleto. Há limite de aproximadamente 6 MiB no log. Dados não exportados se perdem ao encerrar o processo. O componente adicionado não envia o relatório: apenas faz as consultas e requisições documentadas. O navegador original conserva seus próprios comportamentos de rede.

## Validação

Compilação Java/DEX e reconstrução do APK; verificação de assinaturas v1/v2/v3 e alinhamento; integridade ZIP e DEX, resolução das referências internas e preservação do manifesto e dos recursos originais.

Testes JVM com substitutos de APIs Android verificaram: validação de domínio; pacotes DNS válidos, NXDOMAIN/SERVFAIL, IDs e perguntas divergentes, loops de compressão e truncamento; leitura HTTP/DoH com Content-Length e chunked, rejeição de HTML e limites; conclusões proporcionais às evidências; sanitização, limite do buffer, nova sessão limpa e isolamento de resultados antigos.

A V2 não foi executada em Android neste ambiente e as sondas não foram exercitadas na rede do Xiaomi aqui. Os resultados reais virão do log gerado no aparelho. O código-fonte adicionado está em `v2-src/`.
