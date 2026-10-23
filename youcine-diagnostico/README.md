# Diagnóstico nativo do YouCine no MEmu

O log da v2 fornecido pelo usuário registra 731 inicializações completas das
quatro etapas Java, seguidas de 731 encerramentos do processo do aplicativo.
O Zygote registra sinal 9, sem exceção Java ou tombstone nativo que identifique
o motivo. Alterar a entrada Java e adaptar `PackageInfo` não resolveu o ciclo.

A análise estática recuperou segmentos de duas bibliotecas do carregador para
leitura. No código x86_64 de `libexec.so` existem chamadas diretas ao syscall
`kill`, inclusive com sinal 9. Isso é compatível com o log, mas não comprova
qual chamada foi executada, quem a disparou no caso observado ou qual
condição a acionou. Bloquear todas essas chamadas não constitui diagnóstico.

## Coleta única

No Windows PowerShell, execute:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Diagnosticar-YouCine.ps1 -NativeCaller
```

Padrões: ADB em `C:\Program Files\Microvirt\MEmu\adb.exe`, instância
`127.0.0.1:21503`, duração aproximada de 12 segundos.

O script abre o app e o encerra ao final para parar os reinícios. Não instala,
reassina ou altera o APK; não limpa seus dados nem o buffer do logcat. Detecta
root já disponível, sem habilitá-lo ou reiniciar o servidor ADB. Quando o kernel
permite, cria uma instância isolada de ftrace e coleta eventos de `kill`,
`tgkill` e geração de sinais. Também solicita pilhas de usuário; as coletas
anteriores não trouxeram esses endereços, apesar da opção habilitada.

O coletor v2 tenta ainda uma kprobe em `__x64_sys_kill`, para kernel x86_64
com wrapper de syscall e suporte a probes. Ela lê o IP/SP salvo de usuário
em `pt_regs`, além dos argumentos de `kill`. O endereço `user_ip` fica
imediatamente depois da instrução syscall. A mensagem `native_ip_probe=enabled`
confirma a ativação, mas somente um evento `kill_user` com endereço válido
fornece o ponto de chamada. Erros ficam no ZIP. A probe é habilitada apenas
na instância da coleta, com grupo exclusivo e filtro de sinais 6 e 9.
A instância e a definição da probe são desativadas/removidas ao finalizar;
o relatório informa o resultado da remoção da probe.

Também coleta os mapas das bibliotecas dos processos do app, ABI, ponte ARM,
versão do Android, identificação/hash do APK e logcat filtrado. O resultado é
um ZIP na Área de Trabalho. Envie esse ZIP para análise.

Se faltar root ou suporte do kernel, o resumo informa isso. Sem a captura
nativa, o relatório não promete apontar a causa exata. O modo básico não usa
ptrace. O modo `-NativeCaller`, descrito abaixo, usa ptrace para observar o
processo. Nenhum modo usa Frida, hooks de libc ou alterações no carregador.
Sua execução pelo usuário é a coleta solicitada; o agente não executou testes
no dispositivo.

## Como o resultado será interpretado

1. Identificar o emissor e o sinal do evento de encerramento.
2. Associar os endereços capturados ao mapa de memória e à biblioteca correta.
3. Correlacionar o endereço com a rotina recuperada estaticamente.
4. Determinar a condição que chega àquela rotina antes de propor outra mudança.

Uma chamada localizada não prova, por si só, verificação de assinatura,
detecção de emulador ou falha de ABI. Essas causas precisam da correlação
com o código e a condição observada.


## Resultado mais recente

Na coleta da v3.1, a normalização do caminho foi aplicada. Não aparece o
SIGSEGV anterior; uma thread do app emite `kill(0, 9)`. O coletor v2 foi
preparado para tentar obter o endereço dessa chamada, que ainda falta.
Não há confirmação da condição que dispara o encerramento. O histórico
completo das conclusões fica em [RESULTADO.md](RESULTADO.md).


## Coletor v3: observador de syscalls por ptrace

A coleta de 23/10/2026, arquivo `20261023-164558`, informa
`native_ip_probe=unavailable`: não há `kprobe_events` gravável no local
exposto por esse MEmu. O ftrace confirma o sinal e a thread, mas não registra
IP de usuário. Repetir essa mesma coleta não obtém o endereço faltante.

Com `-NativeCaller`, o PowerShell baixa o executável estático x86_64 da
release `youcine-native-diagnostic-v1`, confere seu SHA-256 contra o manifesto
da release e o envia a `/data/local/tmp`. O código-fonte é `native-caller.c`.
O workflow compila com GCC e `-static`; não executa a ferramenta ou o app.
O binário é destinado ao MEmu x86_64 com root já disponível, não a TV Boxes ARM.

Após encerrar a instância anterior do aplicativo, o script inicia o observador
e abre o app. O observador procura o processo pelo cmdline exato do pacote,
anexa via `PTRACE_SEIZE` e acompanha threads novas com `PTRACE_O_TRACECLONE`.
Nos pontos de entrada de `kill`, `tkill`, `tgkill` e `exit_group`, registra o
IP/SP, argumentos, alguns registradores e 32 bytes de instruções ao redor do
IP, além do mapa da thread nesse instante. O IP de entrada aponta imediatamente
após a instrução syscall no Linux x86_64. Não são copiados dados de aplicativo
ou conteúdo da pilha. Saídas e falhas de anexação ficam em `native-caller.txt`.

A ferramenta não modifica registradores, instruções, retornos ou argumentos,
não bloqueia a syscall e encaminha os sinais reais. Ao terminar, tenta
desanexar das threads ainda vivas; não usa `PTRACE_O_EXITKILL`. O script
encerra o aplicativo ao final da coleta, como nas versões anteriores.

Ptrace altera `TracerPid` e o tempo das syscalls. Assim, um ponto capturado
identifica a execução instrumentada; uma verificação de debugger pode mudar
o ramo observado. Isso deve ser correlacionado com o código, sem assumir que
qualquer encerramento instrumentado tem a mesma condição da execução normal.
Nenhum resultado de abertura, compatibilidade ou trial é afirmado nesta entrega.
