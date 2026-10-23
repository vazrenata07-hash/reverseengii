# Resultado das coletas fornecidas pelo usuário

## Coletas da v2 — confirmado

- Android 9, API 28, kernel x86_64; acesso root disponível.
- Pacote selecionado pelo Android como `arm64-v8a` e ponte nativa carregada.
- Na segunda coleta, as quatro etapas Java da v2 apareceram 731 vezes;
  731 encerramentos do processo do app foram registrados.
- Na coleta com ftrace, foram registrados 110 encerramentos do processo do app.
- O evento `sys_kill(pid: 0, sig: 9)` precede a geração de sinal 9 para o app.
  O emissor é uma thread com o nome `world.youcinetv`.
- O ActivityManager realiza a limpeza do grupo posteriormente; ele não é o
  primeiro emissor observado nessa sequência.
- Não há exceção Java fatal ou tombstone nativo identificando a condição.

## O que não foi obtido

Embora `userstacktrace=1` e os eventos estivessem habilitados na instância de
ftrace, a saída não trouxe registros de pilha/endereço de usuário. Portanto,
os mapas coletados não podem ser associados a um endereço específico do sinal.
Os offsets encontrados pela leitura estática não identificam, por si só,
a chamada executada naquela sessão.

## Conclusão da v2

Há encerramento deliberado do grupo por uma chamada de usuário durante a
inicialização original. Não há evidência suficiente para atribuir a condição
exata a assinatura, integridade do arquivo, root ou detecção de emulador.
A mera presença da ponte ARM não demonstra falha de tradução.

A v3 fornece uma imagem assinada original ao carregador para tratar a
inconsistência entre certificado original apresentado em Java e arquivo
recomposto entregue na v2. Isso é uma alteração fundamentada nessa limitação,
mas sua eficácia ainda depende da execução pelo usuário. Não houve teste de
execução pelo agente. Nenhuma coleta bruta de dispositivo foi publicada.


## Coleta da v3 — 20261023-154320

### Confirmado pela coleta

- As etapas Java terminam até `Delegating original application`.
- O processo sofre `SIGSEGV`, `SEGV_MAPERR`, endereço de falha `0x35f`.
- Não há evento de `kill` no rastreamento dessa falha.
- RIP `0x7fd0c063034d`; base da imagem ELF `0x7fd0c05c4000`;
  offset `libexec.so + 0x6c34d`.
- O offset `0x3834d` exibido pelo tombstone usa a base do mapeamento anônimo
  `0x7fd0c05f8000`, não a base ELF.
- A instrução recuperada do carregador x86_64 original é
  `cmp byte ptr [rax + 0x35f], 0`, com `rax = 0` nos registradores do crash.
- O mapa do APK original extraído usa `/data/data`.

### Leitura estática relacionada

A função em `0x6c120` chama, em `0x6c346`, a entrada `+8` da tabela
instalada no campo `+0x40` da estrutura global. A relocação ELF dessa entrada
aponta para `0x48dc0`. Essa função inicia verificações em threads e chama
`0x48950` antes de retornar. Em seguida, `0x6c349` relê a estrutura global
e `0x6c34d` tenta acessar o campo que provocou a falha.

A rotina `0x48950` abre o caminho indicado, lê o caminho associado ao
descritor e o compara com o caminho informado. Em `0x48adc`, a divergência
zera a estrutura global. Essa rotina não emite um sinal nesse ramo; a
continuação com a estrutura nula explica como um crash pode ocorrer sem
um evento de `kill` na coleta.

### Correção da inconsistência no inicializador

A v3 fornecia `File.getAbsolutePath()`, que não resolve aliases. Android
pode informar `/data/user/0` enquanto o kernel retorna `/data/data` para
o mesmo arquivo. A v3.1 passa a obter o caminho pelo próprio descritor,
com `Os.readlink("/proc/self/fd/" + fd)`, antes de preencher `sourceDir`.

O trecho nativo e a falha estão identificados. A coleta não captura os
argumentos efetivos da comparação; portanto, o alias como condição disparada
nessa execução ainda é inferência. A correção elimina essa inconsistência
no código novo, sem afirmar que todas as verificações do carregador foram
satisfeitas. A confirmação da abertura e do trial fica com o usuário.
Nenhum teste de execução foi realizado pelo agente; nenhuma coleta bruta
foi publicada.
