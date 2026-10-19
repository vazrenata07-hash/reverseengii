Mint Android V21 otimizado — fontes da revisão de desempenho

Base: Mint-Browser-v21-danill0.apk. O APK de entrega usa o arquivo mint-rebuilt-danill0.js. A variante de script 87654321 também está incluída nos fontes, sem APK adicional nesta entrega.

PageScripts registra por WebView quando a instalação no início do documento teve sucesso. Nesse caso, os eventos de navegação continuam atualizando a autorização local do contador, mas deixam de reenviar o script completo. WebViews sem suporte continuam usando o fallback anterior. O registro usa referências fracas e só ocorre após a instalação retornar sem erro.

O código de visibilidade consulta a geometria uma vez e obtém o estilo computado uma vez. A classificação de cada campo reutiliza seu contexto de PIN sem guardar resultados entre campos ou entre atualizações da página.

O MutationObserver deduplica raízes adicionadas no mesmo lote, evita procurar novamente dentro de subárvores já cobertas por um ancestral e encerra consultas quando já há uma varredura completa pendente. Mantém a fila de microtasks, os seletores e os intervalos existentes.

A antecipação opcional de imagens do lobby foi removida, incluindo o observador com margem de 600 px e as chamadas de decode. As imagens seguem o carregamento normal do site. Isso reduz trabalho concorrente durante a abertura do CAPTCHA; não é uma medição do ganho nem uma correção comprovada da origem dos três segundos de espera.

O SDK, as chamadas e a validação do CAPTCHA seguem a lógica original. Permanecem o filtro de anúncios, preenchimento, PIN, contador e histórico passivo do JDB Mines 9014. A identificação do navegador e os demais recursos nativos continuam na base V21.

A compilação recompõe somente classes3.dex, com as cinco fontes Java desta pasta, e assets/mint-rebuilt.js. AndroidManifest.xml, classes.dex, classes2.dex e demais recursos são reaproveitados da V21. A assinatura criptográfica é nova; este APK exige reinstalação e não atualiza por cima do APK anterior. Remover a instalação anterior apaga seus dados locais.

Não foram executados testes funcionais, testes automatizados ou benchmarks. Houve compilação, assinatura e revisão estática de código/empacotamento. O resultado no aparelho será verificado pelo usuário.

Reconstrução em Linux com Python 3.10+ e Java 21/keytool: o build-apk.py baixa ferramentas oficiais do Google e o compilador Eclipse ECJ, confere os hashes dos pacotes e compila/assina localmente. É necessário o APK base Mint-Browser-v21-danill0.apk, disponível na raiz do repositório. Os fontes desta pasta correspondem às alterações acrescentadas ao aplicativo; os demais componentes continuam no APK base.

A partir da raiz do repositório:

```sh
python3 src-android-v21-otimizado/build-apk.py \
  --source-dir src-android-v21-otimizado \
  --base-apk Mint-Browser-v21-danill0.apk \
  --work-dir work/android-build \
  --tools-dir work/android-tools \
  --signing-dir work/android-signing \
  --output work/Mint-Browser-v21-Otimizado-danill0.apk
```

A chave e a senha de assinatura ficam em work/android-signing e devem ser preservadas fora do Git para permitir atualizações futuras da mesma instalação. O ZIP de fontes e o repositório não incluem chaves privadas. Uma chave gerada em outra máquina produzirá uma assinatura diferente.
