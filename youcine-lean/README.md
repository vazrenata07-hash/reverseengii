# YC TV 1.15.4 — Lean v3.2 experimental

Base: `yc_1.15.4_ycsite.apk`, release `2.01` deste repositório.
Inicializador próprio em Java para a base TV, voltado a Android 9 e 10.

## Problema tratado

A v3.1 entrega o APK original em
`/data/data/com.world.youcinetv/no_backup/yc_lean/…`. A leitura estática do
carregador original revelou uma rejeição explícita desse layout: na função
`libexec.so+0x48c10`, depois de uma verificação de certificados por JarFile,
o código rejeita um caminho que começa com `/data/` e contém
`/com.world.youcinetv/`. Nesse ramo, zera o caminho interno e chama a rotina
de encerramento com resultado falso. A assinatura e a normalização do caminho
não eliminam essa condição.

A coleta passiva `20261023-172019` localizou três threads em pausas nativas.
A thread que depois emite `kill(0, 9)` estava na rotina `+0x5d560`, com retorno
da pausa em `+0x5d5f0`. Outra thread foi observada em `+0x6d85f`, dentro do
ramo de encerramento `+0x6d830`, com candidatos a retornos em `+0x48d94` e
`+0x48c10`. Os retornos imediatos da espera foram confirmados por opcode e
destino de chamada. A condição do caminho foi identificada pela leitura do
código e das constantes do carregador, não por bloqueio dos sinais.

## Mudança na v3.2

A imagem original passa para a pasta externa específica do aplicativo,
obtida por `Context.getExternalFilesDirs("yc_lean")`. Essa pasta é acessível
pelo próprio app sem root ou solicitação de permissão de armazenamento no
Android 9/10. O contexto é obtido do LoadedApk já vinculado, antes da criação
da Application original; isso usa reflexão em métodos internos do Android.

O inicializador tenta os diretórios disponíveis, mantém a validação de tamanho
e SHA-256 e obtém o caminho real por `Os.readlink("/proc/self/fd/" + fd)`.
Antes de apresentá-lo ao carregador, rejeita o mesmo predicado de layout
identificado no código nativo. A mensagem `Original image location:
app-specific external` distingue essa etapa. Se nenhum diretório for utilizável,
a falha é registrada. O armazenamento externo específico do app precisa estar
disponível para essa estratégia.

A biblioteca nativa original permanece intacta. Não há bloqueio de kill,
modificação de syscalls, ptrace ou ferramenta de diagnóstico dentro do APK.
As outras adaptações da v3.1 permanecem: consultas locais de PackageInfo e
ApplicationInfo, caminhos do LoadedApk e a identidade privada UUID aplicada
a Build.FINGERPRINT antes de delegar à fábrica original. A identidade fica
no armazenamento interno, não junto da imagem externa.

## Estado e limitações da entrega

A coleta localiza rotinas do encerramento e o código novo trata uma condição
que rejeita o caminho fornecido pela v3.1. Não foram capturados todos os
argumentos e resultados das verificações concorrentes; a condição do caminho
não é apresentada como causa única confirmada. A abertura da v3.2, a execução
do player e a renovação do trial ainda dependem dos testes do usuário.

O mod de terceiros não é reutilizado. O carregador protegido original continua
presente. O certificado registrado no Android é o da assinatura de
desenvolvimento, e não existe virtualização completa das verificações nativas.
O player ARM depende da ponte nativa no MEmu x86_64. Gerar outra identidade local
não comprova concessão de novo trial pelo servidor.

O APK inclui a imagem original de aproximadamente 34 MB e fica próximo de
68 MB. A imagem validada é reutilizada nas próximas aberturas. Seu SHA-256 é
`5629c0dc0dc0b631f09bd21f81a5d671e64e6d516cb4a28a9b9fb45a2971b231`.
O certificado original utilizado pelo adaptador tem SHA-256
`0fd3d98319e7dc05830accaedcc9e2af8f3b89234a21a4d4e5ff5e04fecbb2a7`.

## Compilar e publicar

Linux, Python 3.11+ e JDK 17 ou 21:

```sh
python3 build.py
```

Saída: `build/yc-tv-1.15.4-lean-v3.2.apk`. O script confere os insumos,
compila, empacota e assina; não executa o aplicativo nem testes.
O workflow `YC TV Lean Build` publica APK e fontes na release
`yc-tv-1.15.4-lean-v3.2`. Testes de execução ficam com o usuário.
