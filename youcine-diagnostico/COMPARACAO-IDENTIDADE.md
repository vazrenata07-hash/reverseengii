# Comparação da identidade: mod fornecido e Lean v3.2

Base desta comparação: `YOUCINE TV MOD.apk` fornecido, versão 1.15.1,
seu DEX adicional `res/dex/classes.dex` e a biblioteca ARM64 `libnpdcc.so`.
A implementação Lean usa o original TV 1.15.4. São versões diferentes; não
foi obtido o corpo descriptografado dos objetos de autenticação da 1.15.4.
Não se presume que suas chamadas ou classes obfuscadas tenham a mesma forma.

## Resultado informado pelo usuário

O usuário confirmou que a v3.2 abre, mas que o comportamento esperado de
renovação após mudança de identificadores não ocorreu. A compatibilidade de
abertura dessa execução não confirma a rotina de identidade ou o trial.
Nenhum teste de execução foi realizado pelo agente.

## Geração explícita localizada no mod

O código Java dos dois construtores sintéticos utiliza `UUID.randomUUID()`
para o parâmetro `fingerprint` quando a máscara Kotlin solicita esse argumento
padrão. Não é uma substituição de `android.os.Build.FINGERPRINT` global.
O construtor principal recebe o valor e o grava no campo da instância.
Se o chamador fornece fingerprint explicitamente, o caminho de UUID padrão
não é executado. A geração ocorre por chamada desse construtor padrão, não
por um evento obrigatório de inicialização do processo.

| Objeto | Parâmetro fingerprint | Máscara do argumento padrão | Geração |
| --- | --- | --- | --- |
| PreInstallAuthBean | 18º, índice 17 | 131072 / 0x20000 | UUID.randomUUID().toString() |
| SnTokenBean | 16º, índice 15 | 32768 / 0x8000 | UUID.randomUUID().toString() |

Quando ambos são construídos pelo caminho padrão, cada construção pode
receber um UUID diferente, inclusive no mesmo processo. A leitura estática
não demonstra que toda abertura necessariamente construa esses objetos ou
que o servidor conceda novo trial para cada UUID.

## Demais parâmetros dos construtores

Posições contadas a partir de 1, antes da máscara e do marcador Kotlin.

| Campo | PreInstallAuthBean | SnTokenBean | Evidência no mod |
| --- | --- | --- | --- |
| androidId | 3 | 1 | Recebido do chamador; a rotina nativa de leitura usa Settings.System.getString com android_id |
| wifiMac | 4 | 2 | Recebido do chamador; rotinas nativas consultam WifiInfo e NetworkInterface/sysfs |
| etheMac | não existe | 3 | Recebido do chamador; há leitura de interfaces Ethernet e arquivos de endereço |
| serialNumber | 5 | 4 | Recebido do chamador; rotinas nativas leem Build.SERIAL e getSerial por reflexão |
| gatewayMac | não existe | 8 | Recebido do chamador; não foi comprovada geração aleatória |
| cpuId | não existe | 9 | Recebido do chamador; não foi comprovada geração aleatória |
| fingerprint | 18 | 16 | UUID explícito nos construtores padrão descritos acima |

Os campos display, brand, verId, cpuAbi, hardware, manufacturer, host,
device, board (quando existente) e tags utilizam valores Build em seus
argumentos padrão. Não foi identificada nesses construtores uma randomização
geral do aparelho ou de todos os campos MAC.

## Parte nativa conferida

As tabelas JNI de libnpdcc foram recuperadas pela leitura de suas rotinas de
registro, com ambiente JNI sintético apenas para materializar os metadados.
Nenhum app, requisição de rede ou API real de Android foi executado.
Os corpos ARM64 foram examinados por leitura e anotação das instruções.

- `ka.c0.j(Context)`, em `libnpdcc+0xf676c`, obtém o ContentResolver e chama
  `Settings.System.getString` com a chave `android_id`.
- `ka.c0.y(Context)`, em `+0xee53c`, chama WifiManager.getConnectionInfo e
  WifiInfo.getMacAddress.
- `ka.c0.o()`, em `+0xe96ec`, e `ka.c0.z()`, em `+0xef054`, usam
  NetworkInterface.getByName/getHardwareAddress. Há caminhos de fallback para
  `/sys/class/net/eth0/address`, `/sys/class/net/wlan0/address` e outras interfaces.
- `ka.c0.v()`, em `+0xff830`, consulta Build.SERIAL e chama a rotina de
  fallback `w()`, que usa reflexão para obter o serial.

Esses pontos consultam identificadores do sistema. A presença de MAC nos
objetos não demonstra falsificação de MAC. Não se afirma que todos os ramos
nativos ou chamadas anteriores aos construtores tenham sido reconstruídos.

A rotina `i2.f.A(String,String,String)`, em `libnpdcc+0xaf3dc`, termina sem
operar escrita de propriedades: depois das verificações JNI e do gerenciamento
de referências, retorna. Os parâmetros não são usados para gravar o conteúdo.
O módulo contém rotinas que leem arquivos Properties, referências a
`/sdcard/.properties` e chamadas de `z(String,String)` para esse ponto de
gravacão. Portanto, existe uma diferença de persistência relevante além do
UUID dos objetos. Sem um binário limpo da mesma versão 1.15.1, não se apresenta
isso como um diff completo contra o original do fornecedor.

Também existem chaves de estado como `key_preinstall_flag`, `key_device_id`,
`key_sn_token`, `key_sn_flag`, `key_user_identity`, `KEY_SP_SN` e `SP_SN_BACKUP`.
Sua presença não autoriza concluir que todas são apagadas em cada abertura.
O fluxo exato de leitura/gravação dessas chaves na 1.15.4 continua a verificar.

## O que Lean v3.2 realmente implementa

`InstallIdentity.readOrCreate` grava um UUID em
`no_backup/yc_lean/identity-v1` e o reutiliza até a limpeza dos dados.
`EarlyFactory.prepare` atribui esse valor ao campo Java Build.FINGERPRINT
antes do carregador protegido original.

Não há interceptação de PreInstallAuthBean ou SnTokenBean, alteração direta
dos seus argumentos, nem substituição das rotinas de backup identificadas
acima. Também não há alteração de Android ID, MAC, serial, SN/token ou das
chaves de sessão do aplicativo.

| Aspecto | Mod fornecido | Lean v3.2 |
| --- | --- | --- |
| Ponto de mudança explícita | fingerprint dos objetos de autenticação | Build.FINGERPRINT no processo |
| Duração do UUID | Novo por construção pelo caminho padrão | Persistido até limpar dados |
| Relação entre os dois objetos | Podem receber valores diferentes | Mesmo UUID global |
| Backup Properties | Ponto A examinado não grava | Rotinas originais 1.15.4 preservadas |
| Valor efetivamente enviado ao servidor | Há geração explícita nos objetos do mod | Não foi observado na 1.15.4 |

Essa implementação não reproduz a rotina do mod. Atribuir Build.FINGERPRINT
não prova que o campo fingerprint da requisição protegida 1.15.4 receba esse
valor, e trocar a duração do UUID, isoladamente, também não demonstra isso.
A falha demonstrável é a diferença de mecanismo; a causa exata do resultado
no servidor não foi capturada.

## Limpar dados e limpar cache

Limpar dados remove preferências, bancos e tokens privados, além de cache.
Isso pode fazer o app executar novamente cadastro/autenticação que antes
reutilizava estado local. Limpar só o cache não produz a mesma ação.
No mod, o UUID não depende de um arquivo próprio de identidade nos dois
construtores examinados. Isso não significa que toda sessão ou identidade
mantida pelo restante do app seja recriada em cada abertura.

## Implementação v3.3

A v3.3 mantém a solução de abertura da v3.2 e remove o UUID persistente e a
alteração global de Build.FINGERPRINT. Em seu lugar instala callbacks dos
construtores padrão dos dois objetos, condicionados ao formato de parâmetros
e campos da referência. O callback aplica UUID apenas quando o bit padrão de
fingerprint está ativo, limpa esse bit e delega ao construtor original.

Uma regra separada reconhece a classe de persistência pelo formato dos campos
e métodos e omite a escrita Properties de três Strings. Não presume que o
nome obfuscado da referência se mantenha: ausência ou ambiguidade é registrada.
`i2.f.t()` também foi identificado como rotina vazia na referência; só recebe
callback quando esse nome e o formato da classe estão presentes.

O motor LSPlant/Dobby é compilado para quatro ABIs, com regras próprias e
carregamento após Application.attach. Ele não utiliza o carregador nem a
biblioteca Dex2C do mod. As assinaturas efetivas da 1.15.4 ainda são verificadas
no próprio processo antes de instalar cada callback. Não houve testes do app;
o usuário verificará abertura, instalação dos callbacks e efeito do servidor.
