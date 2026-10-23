# Resultado das coletas fornecidas pelo usuário

## Confirmado

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

## Conclusão técnica atual

Há encerramento deliberado do grupo por uma chamada de usuário durante a
inicialização original. Não há evidência suficiente para atribuir a condição
exata a assinatura, integridade do arquivo, root ou detecção de emulador.
A mera presença da ponte ARM não demonstra falha de tradução.

A v3 fornece uma imagem assinada original ao carregador para tratar a
inconsistência entre certificado original apresentado em Java e arquivo
recomposto entregue na v2. Isso é uma alteração fundamentada nessa limitação,
mas sua eficácia ainda depende da execução pelo usuário. Não houve teste de
execução pelo agente. Nenhuma coleta bruta de dispositivo foi publicada.
