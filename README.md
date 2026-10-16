# Mint Browser V8 — dois APKs sem ZIP

| Variante | Download |
| --- | --- |
| Senha `danill0` | [Mint-Browser-v8-senha-danill0.apk](Mint-Browser-v8-senha-danill0.apk) |
| Senha `87654321` | [Mint-Browser-v8-senha-87654321.apk](Mint-Browser-v8-senha-87654321.apk) |

Abra o APK desejado e clique em **Download raw file** (ícone de download). Não é necessário extrair arquivos.

## Alterações

- Usuário aleatório alfanumérico de **15 caracteres**, renovado a cada entrada em `/register`, em `888pg.cc` e seus subdomínios.
- Senha e confirmação preenchidas com a senha da variante escolhida.
- Mantido o detector da V7; não foi aplicada a proposta de torná-lo mais conservador.
- Ampliada somente a exceção de envelopes/sacos vermelhos e chuva de envelopes: contempla identificadores adicionais e o caso em que a animação e a janela principal pertencem a camadas irmãs, inclusive quando a animação aparece depois da janela.
- Mantidas as exceções anteriores para CAPTCHA, baús/presentes, recompensas e rotas de cadastro/login. Sem cliques automáticos no botão de fechar.
- Permanecem removidos os antigos filtros por classe genérica e os bloqueios fixos de API.

As duas variantes usam o mesmo pacote e a mesma versão; instale a variante da senha desejada. Elas substituem uma à outra.

## Validação

Testes de lógica/DOM passaram nas duas variantes: 15 caracteres, renovação por rota, senhas, CAPTCHA, exceções de recompensa, camadas de envelopes separadas e restauração tardia. Compilação, alinhamento e assinatura verificados. O comportamento da janela no site real ainda precisa ser validado pelo usuário; imagens de tela não fornecem a estrutura DOM exata.

## SHA-256

- `Mint-Browser-v8-senha-danill0.apk`: `83217e5ef173cabe53e972f23d3b32744c262b7a9b27320119a94640db1d2e96`
- `Mint-Browser-v8-senha-87654321.apk`: `3fb92f118f1d9df5d127661ebabff7713178ad61d23aaec2a092088a685df660`

V5, V6 e V7 ficam no repositório apenas como versões anteriores.
