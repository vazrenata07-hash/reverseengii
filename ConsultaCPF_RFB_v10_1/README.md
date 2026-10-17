# Consulta CPF RFB v10.1 — Teste sem janela

[Baixar ZIP completo](../ConsultaCPF_RFB_v10_1_Headless_Teste.zip)

Execute `iniciar.bat`. Em **Settings**, marque **Navegador sem janela (headless — experimental)**,
salve e inicie uma lista pequena. Para isolar o teste, deixe a troca Wi-Fi desligada.
O aplicativo mostra os resultados enquanto o Edge/Chrome executa sem janela.

Se a verificação não liberar a consulta em 30 segundos após o formulário carregar,
o programa para e preserva os resultados. Desmarque a opção e clique em Iniciar
para continuar com navegador visível. O modo visível continua sendo o padrão.

O navegador ainda executa JavaScript e a verificação original. Não é HTTP direto.
Sem garantia de economia adicional de banda apenas pela ausência da janela.

Validação: 24 testes automatizados, interface Tk em tela virtual e Chromium real
em headless contra formulário HTTP local com JavaScript e preenchimento.
Receita/CAPTCHA real e Windows/Edge ainda não foram testados.

As configurações de redes Wi-Fi da v10 permanecem disponíveis. Veja [LEIA-ME.txt](LEIA-ME.txt).
Testes: `python -m unittest discover -s tests`. Para novo EXE: `gerar_exe.bat`.
