# YC TV 1.15.4 — Lean v2 experimental

Base: `yc_1.15.4_ycsite.apk`, release `2.01` deste repositório.
Implementação própria em Java, sem reutilizar o carregador do mod TV.
Ambientes de interesse: Android 9 e 10, incluindo MEmu Android 9 x64.

## Mudança na v2

O log fornecido pelo usuário após executar a v1 registrou 1.608 encerramentos
de processo por sinal 9 e nenhum registro `YCLean`. A v1 só inicializava por
um provider, depois da etapa que está encerrando o processo. O log não revela
quem envia o sinal nem comprova a causa do encerramento.

A v2 troca o ponto de entrada para `EarlyFactory`, antes de delegar à fábrica
original `s.h.e.l.l.A`. No Android 9, obtém `ApplicationInfo` do processo
vinculado; no Android 10, recebe essa informação em `instantiateClassLoader`.

- Identidade UUID v4 persistente em `no_backup/yc_lean/identity-v1`.
- A identidade é aplicada a `Build.FINGERPRINT` antes da delegação original.
- Limpar todos os dados elimina a identidade; limpar só o cache não elimina.
- Adaptador local de `PackageInfo` usa o certificado público extraído do APK
  base nas consultas sobre o próprio pacote. Inclui `signatures` e, quando
  acessível, `SigningInfo`. A adaptação é uma tentativa de compatibilidade com
  a nova assinatura; o log não comprovou que a assinatura causa o sinal 9.
- As etapas anteriores à delegação registram mensagens `YCLean`, inclusive
  quando uma operação opcional não pode ser aplicada.

Os componentes continuam sendo criados pela fábrica original. O conteúdo
dos demais arquivos do APK é preservado. Não há bibliotecas nativas próprias,
serviços, telas ou permissões novas. O antigo provider da v1 foi removido.

## Limites técnicos e estado

Compilado e publicado, sem testes executados pelo agente, conforme solicitado.
O usuário realiza os testes nos dispositivos. A correção do encerramento e a
renovação do trial não estão confirmadas.

A referência concreta do mod é o uso de `UUID.randomUUID()` no fingerprint
dos construtores de `PreInstallAuthBean` e `SnTokenBean`. Não foi confirmado
que a versão protegida 1.15.4 utilize o campo nas mesmas condições. A identidade
local nova não garante a concessão de trial pelo servidor.

O adaptador atua em objetos Java retornados por `PackageInfo.CREATOR`; não
altera o certificado registrado pelo Android nem a verificação direta do
arquivo APK. O carregador protegido original e as bibliotecas ARM do player
permanecem. O MEmu precisa de tradução ARM compatível. O APK recomposto tem
assinatura de desenvolvimento e não instala como atualização do original.

## Compilar

Linux, Python 3.11+ e JDK 17 ou 21:

```sh
python3 build.py
```

Saída: `build/yc-tv-1.15.4-lean-v2.apk`. O script baixa as ferramentas e o APK
base, confere os hashes dos insumos, compila, empacota e assina. Não executa
o aplicativo nem testes. A verificação do assinador faz parte da geração.

O workflow `YC TV Lean Build` publica APK e fontes na release
`yc-tv-1.15.4-lean-v2`.
