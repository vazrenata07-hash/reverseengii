# Mint Browser V9 — APKs diretos

| Senha | APK |
| --- | --- |
| `danill0` | [Mint-Browser-v9-senha-danill0.apk](Mint-Browser-v9-senha-danill0.apk) |
| `87654321` | [Mint-Browser-v9-senha-87654321.apk](Mint-Browser-v9-senha-87654321.apk) |

Abra o APK e clique em **Download raw file** (⬇). Sem ZIP.

## Correção específica da V9

Adicionadas exceções explícitas, em `888pg.cc` e subdomínios, para os componentes apontados pelo usuário:

- `div._fastBtn_3tzh2_99`
- `div.lobby-image.lobby-image--use-bg._fastBackground_3tzh2_112`
- `img.lobby-image._closeIcon_3tzh2_141`
- `img.lobby-image._fastImg_3tzh2_117`

Esses seletores são usados para **preservar**, nunca para ocultar. O detector protege o componente e seus contêineres, inclusive quando os elementos chegam depois. Os nomes específicos de fastBtn/fastBackground/fastImg também aceitam uma mudança do hash do CSS. Não foi aplicada a proposta de restringir o bloqueio geral a elementos pequenos nas bordas.

## Mantido

- Usuário aleatório alfanumérico de **15 caracteres**, renovado em cada entrada em `/register`, em `888pg.cc` e subdomínios.
- Senha e confirmação conforme a variante escolhida.
- Exceções de CAPTCHA e recompensas, sem cliques automáticos de fechamento.
- Filtros antigos por classe genérica e bloqueios fixos de API continuam removidos.
- As duas variantes substituem uma à outra; escolha a senha desejada.

## Validação

Passaram os testes nas duas variantes: seletores exatos, alteração do hash, conteúdo inserido depois, geração de 15 caracteres, senhas, rotas, CAPTCHA e demais exceções. Compilação, alinhamento, assinatura e conteúdo do DEX verificados. A janela real ainda precisa de validação no aparelho.

## SHA-256

- `Mint-Browser-v9-senha-danill0.apk`: `571032c0290cfd8d075db26fff143959a431d5c4cf09fa256b1661686275a4af`
- `Mint-Browser-v9-senha-87654321.apk`: `fc0a8ee8330a4e343aff9378bf6901709a67a87c79853bc6e45ce3f4227e4024`

As versões anteriores ficam disponíveis apenas como histórico.
