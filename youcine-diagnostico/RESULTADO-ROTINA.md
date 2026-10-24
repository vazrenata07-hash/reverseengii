# Resultado do log youcine-rotina.txt

## Atualizacao: youcine-crash.txt, v3.3.2

O motor agora inicia: `ART identity runtime ready=true VM ABI=x86_64
loader=isolated`. A regra Properties registra instalacao em o2.g.A.
PreInstallAuthBean e SnTokenBean nao foram encontradas no pacote com.request.bean
durante a instalacao do provider. Nao ha mensagem de uso dos callbacks de
fingerprint no arquivo recebido.

A terminacao e uma excecao Java em AppWrapper.onCreate, com a mensagem:

```text
Attempt to invoke virtual method 'me.jessyan.autosize.AutoSizeConfig
me.jessyan.autosize.AutoSizeConfig.setPrivateFontScale(float)'
on a null object reference
```

A pilha aponta AppWrapper.H(SourceFile:9), AppWrapper.onCreate(SourceFile:32)
e Instrumentation.callApplicationOnCreate. Esse erro e diferente da falha de
arquitetura anterior. O log nao mostra qual chamada anterior forneceu o
objeto nulo nem estabelece uma relacao causal com o hook Properties.

A v3.3.3 retira a inicializacao do motor e das regras da fase de providers.
Usa uma fronteira apos o retorno do Application.onCreate original, restaura
a Instrumentation padrao antes de entrar no app e registra os callbacks na
Application criada. Procura os beans pelo nome simples nos DEX presentes,
mantendo validacao do formato e rejeicao de nomes ambiguos. Nomes relacionados
sao registrados para distinguir renomeacao de indisponibilidade nessa fase.
A abertura e o efeito da rotina permanecem para os testes do usuario.

## Atualizacao: coleta 20261023-181826-899

O SHA-256 corresponde exatamente ao APK v3.3.1 publicado. A descoberta por
mapas encontrou o ART, mas o motor falhou antes de instalar callbacks:

```text
ART discovery phdr=0 maps=5 candidates=1 vm_bits=64
ART symbols parsed=17 source=/system/lib64/libart.so bias_source=maps sections=11
Failed to find GetMethodShorty
Failed to init art method
ART hook initialization ready=0
```

Os mapas do PID 13305 mostram o auxiliar em yc_identity/arm64-v8a, com
permissoes r--p, e libhoudini.so no processo. O ART real e a biblioteca
x86_64 /system/lib64/libart.so. Sua copia obtida por ADB tem 29 secoes e o
simbolo local _ZN3artL15GetMethodShortyEP7_JNIEnvP10_jmethodID em 0x404340.
Portanto, o simbolo existe no ART fornecido, mas nao foi visto na leitura
do auxiliar ARM64 traduzido. Nao se conclui que falte o simbolo no emulador.

A selecao por os.arch feita na v3.3.1 levou ao auxiliar ARM64. A v3.3.2
troca essa origem pelo ELF do executavel da VM e usa um loader separado,
sem pai no namespace ARM da aplicacao, com registro JNI explicito para as
classes de regras. Mantem a estrategia de abertura da v3.2. O proximo
resultado precisa mostrar a ABI real do auxiliar e a inicializacao do motor;
os callbacks nao foram executados com sucesso na coleta recebida.

## Coleta anterior: v3.3

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
