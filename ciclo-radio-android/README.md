# Ciclo de rádio

Aplicativo Android que usa acessibilidade para desligar e religar a chave **Potência de rádio móvel** na tela de informações do telefone, em intervalos escolhidos pelo usuário.

Versão **1.2**. O aplicativo funciona sem conta ou anúncios e consulta o ipify por HTTPS, exclusivamente pela rede móvel, para confirmar o IP público de saída. Não exige root. Android mínimo: **8.0 (API 26)**. Compilado com API 35.

## Instalação e uso

1. Baixe o arquivo `ciclo-de-radio.apk` deste repositório e instale no telefone. Se solicitado, permita a instalação pelo navegador ou gerenciador de arquivos utilizado.
2. Abra **Ciclo de rádio**. Permita verificar chamadas e ative o serviço de acessibilidade do aplicativo. A permissão de telefone permite adiar ciclos durante chamadas.
3. No Android 13 ou posterior, se a acessibilidade estiver restrita, abra **Informações do app → menu ⋮ → Permitir configurações restritas**. A localização desse menu depende do fabricante.
4. Configure o intervalo, de 10 segundos a 24 horas, e a pausa desligado, de 1 a 10 segundos. Comece por **Testar um ciclo agora**.
5. Se o atalho não abrir a tela correta, abra manualmente **Informações do telefone**, deixando a chave de rádio visível, e teste novamente.
6. Para repetir, toque em **Iniciar ciclos** e deixe o app aberto, com a tela ligada e desbloqueada. Para encerrar, use **Parar e religar** antes de desativar a acessibilidade.

## Comportamento e limites

- O intervalo só começa após uma consulta HTTPS pela rede móvel confirmar o IP público de saída. A reconexão não consome o intervalo: com 10 segundos configurados, são 10 segundos completos depois dessa confirmação. Isso vale também no início da rotina.
- Enquanto aguarda o IP, inicia novas tentativas a cada segundo, com concorrência limitada e limites curtos de conexão e leitura. A primeira resposta válida libera a contagem e encerra as consultas restantes. A consulta começa assim que a rede móvel aparece; não espera a validação separada do Android. A cadência não garante que o servidor responda em um segundo.
- Se a rede móvel cair durante a contagem, o app aguarda a reconexão, confirma novamente o IP público e reinicia o intervalo completo. Wi-Fi não confirma a conexão móvel.
- O teste executa um ciclo imediatamente. A pausa desligado começa quando a interface confirma a chave desligada.
- Desligar e religar essa chave é uma função do aparelho e não costuma causar dano físico. Interrompe temporariamente dados móveis, hotspot, chamadas e SMS; ciclos frequentes podem aumentar o consumo de bateria. Em alguns aparelhos, a chave afeta os dois chips.
- A reconexão pode demorar mais que a pausa configurada. O app mostra “Aguardando conexão e IP público” nesse período e não dispara outro ciclo antes da confirmação. A operadora pode fornecer o mesmo IP novamente: a confirmação verifica que há internet móvel com IP público de saída, sem exigir que ele tenha mudado. Se o ipify estiver indisponível, a contagem aguarda uma consulta bem-sucedida.
- O serviço procura a chave de rádio pelos identificadores conhecidos ou pelos rótulos exatos em português e inglês. Telas de outros fabricantes podem exigir adaptação. O app não altera o tipo de rede, DSDS ou provisionamento.
- Se não localizar a chave ou confirmar seu estado, o app informa a situação e pode pedir religamento manual. Se o Android encerrar o processo enquanto o rádio estiver desligado, pode ser necessário reabrir o app ou religar a chave manualmente.
- O APK foi compilado. Não foram executados testes em aparelho ou emulador nesta atualização, conforme solicitado.

## Compilar

Requisitos: Linux ou macOS com Bash, JDK 17 ou posterior (`java`, `javac` e `keytool`), Python 3 e Android SDK com os pacotes oficiais **platforms;android-35** e **build-tools;35.0.1**. Instale os pacotes pelo SDK Manager do Android Studio ou por `sdkmanager`:

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.1"
export ANDROID_SDK_ROOT="/caminho/para/Android/Sdk"
./build.sh
```

O resultado será `build/ciclo-de-radio.apk`. O script compila as fontes, converte para DEX, alinha e assina o APK e verifica a assinatura. Nenhum SDK ou biblioteca de terceiros acompanha o repositório.

Se nenhuma chave for indicada, o script cria uma chave local de desenvolvimento em `.local-signing/`, excluída do Git. Para usar uma chave própria, configure `KEYSTORE_FILE`, `KEY_ALIAS`, `KEYSTORE_PASSWORD` e `KEY_PASSWORD` antes de compilar. A chave usada no APK pronto **não está incluída**; uma compilação com outra chave exige desinstalar o APK anterior antes da instalação.

Para conferir o APK distribuído, compare seu SHA-256 com `SHA256SUMS`:

```bash
sha256sum -c SHA256SUMS
```

A consulta ao ipify transmite apenas a requisição necessária para identificar o IP de saída; não envia o conteúdo da tela, números de telefone ou dados de consultas. O último IP confirmado fica nas preferências privadas do app.

Código-fonte sob licença MIT. O aplicativo não tem vínculo com fabricantes, operadoras ou órgãos públicos.
