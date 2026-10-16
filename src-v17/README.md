# Mint V17

Duas variantes com o mesmo código e assinatura: senha danill0 e senha 87654321. Gerador de usuário permanece com 15 caracteres. Regras de anúncios da V16, código inicial e Limpar dados preservados.

Desempenho: alterações de estilos de animações, SVG/Lottie e contadores fora dos pop-ups não disparam buscas completas. Reavaliação do filtro limitada a mudanças dos componentes conhecidos; formulário reavaliado quando entradas/rotas mudam. Estilo de pop-up conhecido ainda é observado para fechar componentes reutilizados com display:none/block. Imagens img.lobby-image próximas recebem loading=eager/decoding=async por um observador separado, sem trocar URLs ou substituir o IntersectionObserver do site.

Certificados: os três callbacks SSL da cadeia de navegação chamam SslErrorHandler.proceed diretamente, antes de delegação, fila e criação do diálogo. Isto permite conexões apesar de erros de certificado recuperáveis. A validação interna do Android System WebView continua existindo; não é possível desligá-la pela API pública do APK. Erros de protocolo TLS não recuperáveis não são corrigidos por esta mudança.

Validação: testes Chromium com seletores capturados, fechamento nativo, recompensas não classificadas, CAPTCHA/navegação, pop-up reutilizado e animação de saída. No cenário de 40 atualizações de animação/contador, buscas completas caíram de 360 para 0; isso não equivale a uma medição de FPS no aparelho. Senhas e confirmações validadas em ambas as variantes. APKs alinhados, assinaturas v1/v2/v3 verificadas e conteúdos comparados: só o script da senha difere, além das assinaturas. Sem execução Android; rolagem e conexão SSL precisam de validação no aparelho.
