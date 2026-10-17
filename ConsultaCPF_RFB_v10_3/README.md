# Consulta CPF RFB v10.3 — CAPTCHA compacto

[Baixar ZIP completo](../ConsultaCPF_RFB_v10_3_CAPTCHA_Compacto.zip)

Execute `iniciar.bat`. Em **Settings**, a antiga opção headless foi substituída
por **Mostrar somente o CAPTCHA no canto superior direito**. Marque, salve e
inicie a consulta (pare e inicie novamente se já estava em execução).

A barra de progresso fica curta. A verificação usa uma janela real do navegador
incorporada na área superior direita, com clique inicial automático e interação
manual disponível. **Ampliar** abre espaço para desafios; **Reduzir para o canto**
retorna ao painel. Desmarcada a opção, o navegador abre normalmente.

As redes Wi-Fi e a retomada das consultas foram mantidas. Para detalhes e
limitações, veja [LEIA-ME.txt](LEIA-ME.txt).

Validação: 24 testes, interface Tk em tela virtual e Chromium real contra um
checkbox local em iframe. A incorporação Win32 e o CAPTCHA real ainda precisam
ser validados no Windows. O teste local não comprova liberação pelo serviço.

Testes: `python -m unittest discover -s tests`. EXE: `gerar_exe.bat`.
