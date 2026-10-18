# Consulta CPF RFB v10.4.2 — Somente CAPTCHA

[Baixar ZIP completo](../ConsultaCPF_RFB_v10_4_2_Responsivo.zip)

Execute `iniciar.bat`. Em **Settings**, marque **Mostrar somente o CAPTCHA no
canto superior direito**, salve e inicie novamente a consulta.

**Contador ajustado:** a troca por intervalo só começa a contar após a primeira
verificação válida do CAPTCHA no IP atual. Não conta carregamento ou conexão e
não reinicia a cada CPF. A cada rede/IP novo, aguarda outra primeira verificação.

**Responsividade:** a captura da imagem tem conexão e thread próprias, sem
bloquear clique ou leitura do resultado. A API de verificação é tentada assim
que está pronta; uma resposta inicial de espera não desativa a tentativa.
A pausa fixa após envio do formulário foi removida.

O painel mostra apenas o recorte atualizado do widget real. Não incorpora uma
janela inteira e não mostra abas, endereço ou HTML restante. Clicar no painel
encaminha a interação ao CAPTCHA. **Ampliar** mostra o recorte do desafio.
O resto da página é processado internamente para atualizar a situação na tabela.

O envio de um clique é apenas uma tentativa: a confirmação depende de detectar
o desafio ou token de resposta. Sem confirmação, o painel permite clique manual.
O navegador continua executando a sessão original fora da área visível.
Não há promessa de economia adicional ou de liberação automática do CAPTCHA.

Validação: 34 testes, teste de imagem bloqueada sem bloquear clique, interface Tk em tela virtual e Chromium real com formulário
HTTP local, recorte e clique encaminhado. CAPTCHA real e Windows/Edge ainda
precisam de validação. Nenhuma consulta externa de CPF foi realizada nos testes.

Detalhes em [LEIA-ME.txt](LEIA-ME.txt). Para EXE: `gerar_exe.bat`.
Testes: `python -m unittest discover -s tests`.
