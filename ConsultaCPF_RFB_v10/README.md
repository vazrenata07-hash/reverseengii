# Consulta CPF RFB v10 — Redes Wi-Fi

[Baixar ZIP completo](../ConsultaCPF_RFB_v10_WiFi_Settings.zip)

Use **Settings** para adicionar os **nomes reais (SSID)** das redes, digitados ou
selecionados na lista detectada. As redes precisam estar salvas no Windows.
Escolha troca a cada X segundos ou quando a verificação não iniciar em 2 segundos
após o formulário carregar. O desafio aberto continua manual.

A troca fecha o navegador dedicado, aguarda o Windows confirmar a próxima rede
e retoma o CPF pendente, preservando resultados. Confira [LEIA-ME.txt](LEIA-ME.txt)
para instruções, limitações e validação. Não há novo sistema de proxy nesta versão.

Execute `iniciar.bat`, ou gere um novo EXE com `gerar_exe.bat`.

Validação: 18 testes locais e interface Tk executada em tela virtual com Wi-Fi
simulado. Troca física de Wi-Fi e execução no Windows ainda precisam de validação.

Testes: `python -m unittest discover -s tests`.
