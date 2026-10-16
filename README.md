# Mint Browser V10 — APKs diretos

| Senha | APK |
| --- | --- |
| `danill0` | [Mint-Browser-v10-senha-danill0.apk](Mint-Browser-v10-senha-danill0.apk) |
| `87654321` | [Mint-Browser-v10-senha-87654321.apk](Mint-Browser-v10-senha-87654321.apk) |

Abra o APK e clique em **Download raw file** (⬇). Sem ZIP.

## Correção da V10

A exceção do componente `_fastBtn_3tzh2_99`, `_fastBackground_3tzh2_112`, `_closeIcon_3tzh2_141` e `_fastImg_3tzh2_117` agora cobre os caminhos de ocultação personalizados **e nativos** em `888pg.cc` e seus subdomínios.

- O detector marca o componente e seus ancestrais como protegidos para o adblock nativo.
- `assets/adblock/css.js`: as regras nativas deixam de atingir os elementos protegidos; isso funciona também quando a regra é inserida antes de o componente ser montado.
- `assets/adblock/hide.js`: a ocultação inline nativa respeita a proteção e registra valores anteriores para restaurar o que ela própria ocultou antes de o componente aparecer.
- O filtro personalizado usa apenas seu atributo CSS para ocultação; não sobrescreve mais `display`, `visibility` e `pointer-events` inline do site. Remover o bloqueio não repõe um estado antigo por cima da animação atual.
- A classificação geral dos demais flutuantes foi mantida; não foi aplicada a proposta de limitar o detector às bordas.

## Mantido

Usuário aleatório de **15 caracteres** em cada entrada em `/register`; senha e confirmação conforme a variante; exceções de CAPTCHA e recompensas; sem cliques automáticos de fechamento. As duas variantes substituem uma à outra.

## Validação

Testes com os scripts reais de CSS e ocultação inline do adblock nativo, seletores exatos e ancestrais, regras antes da montagem, montagem posterior e preservação dos estilos de animação passaram nas duas senhas. Também passaram as verificações anteriores de geração de usuário, rotas e CAPTCHA, compilação, assinatura e alinhamento. A janela do site real ainda precisa de teste no aparelho.

## SHA-256

- `Mint-Browser-v10-senha-danill0.apk`: `0b19cdf2115c27cc1baaa225561fae77e4b69e7cf8d4e09c2fb7927fa572a96c`
- `Mint-Browser-v10-senha-87654321.apk`: `83651f31bda33d3b4c49e9249b48790020842d63371fed51c7c24ba81d1fa00d`

As versões anteriores ficam apenas como histórico.
