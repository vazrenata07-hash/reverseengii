# V25: janela inicial compacta

Base: Mint-Browser-v25-PIN-Fluido-danill0.apk, SHA-256 8fb6130873aeff23840a463f45a36225e5ca96a9e2ff90a452aff193a1872720.

- Abrir com o campo vazio (incluindo espaços) abre a página inicial, sem exigir 0.
- Código preenchido mantém a regra de pelo menos 7 dígitos. O valor 0 isolado passa a ser inválido.
- Janela com largura de 220 dp, limitada à largura disponível, altura ajustada ao conteúdo e sem título/texto explicativo. Campo com dica “Código (opcional)”. O tamanho visual exato depende do tema e da tela; objetivo aproximado de um terço da área anterior.
- Teclado permanece oculto ao abrir; tocar no campo permite digitar.

Somente Bootstrap e Bootstrap$3 foram alterados no classes3.dex. Manifesto, recursos, bibliotecas, demais classes e script integrado são idênticos à v25. Não houve alteração na automação GeeTest.

Verificações: recompilação smali, comparação de todas as entradas do APK, comparação das demais classes do DEX e validação de alinhamento/assinatura v1/v2/v3. Sem emulador/aparelho disponível; interface e navegação precisam de teste no Android.

APK assinado com certificado de teste diferente do original. Não instala como atualização da v25 original. Reinstalar pode ser necessário e desinstalar apaga dados locais; preserve os dados antes. Esta variante mantém o pacote e a versão da base.

SHA-256 do APK: 270f7511042ce78f78b925dda17012ab432e329f8482337defbc44c3c4e9d64d.

Reprodução: decodificar a base com Apktool 2.12.1 (-r), aplicar patch-dialog.py ajustando o caminho root, recompilar e substituir apenas classes3.dex no ZIP original; remover metadados antigos de assinatura e alinhar/assinar. Arquivos Bootstrap*.smali incluídos para revisão da implementação final.
