# Resultado do log youcine-rotina.txt

O arquivo fornecido apos a v3.3 contem historico de varias versoes. As duas
execucoes identificadas como v3.3 tem PIDs 8145 e 8691. Ambas registram:

```text
ART symbols unavailable; identity rules disabled
```

Essa mensagem pertence a JNI_OnLoad do auxiliar novo. Confirma que a
biblioteca carregou e que ArtSymbols::load retornou falso antes de chamar
LSPlant::Init. Portanto, nessa execucao o caminho novo nao chegou a instalar
os callbacks. O estado VIP expirado nao pode ser atribuido a um UUID novo
aplicado com sucesso por essa rotina.

Na v3.3, o resolvedor depende de dl_iterate_phdr para localizar libart.so,
depois abre seu ELF e extrai as tabelas de simbolos. Qualquer falha nessas
etapas produz a mesma mensagem. O log nao distingue biblioteca ausente da
enumeracao, erro de abertura ou tabelas indisponiveis. Os mapas ja fornecidos
nas coletas anteriores mostram libart em /system/lib64/libart.so no MEmu;
isso confirma sua presenca naquelas coletas, sem provar a subetapa que
falhou nas duas execucoes da v3.3.

A v3.3.1 acrescenta descoberta por /proc/self/maps, calculo do load bias
por PT_LOAD, verificacao do tipo de maquina ELF e mensagens por subetapa.
Conserva a origem dl_iterate_phdr e a estrategia de abertura externa da v3.2.
Nao altera novamente os parametros de autenticacao com base nessa falha.

O coletor Diagnosticar-Rotina-YouCine.ps1 registra apenas mensagens novas
para seu resumo, e separa o historico anterior. Inclui metadados do APK,
PIDs, providers, mapas relevantes e copias publicas de libart.so quando
acessiveis, permitindo conferir o proximo ponto sem um dump de sessao ou
memoria do aplicativo. Testes de execucao permanecem com o usuario.
