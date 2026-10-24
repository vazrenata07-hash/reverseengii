Patch **v2 aplicado ao mod original de terceiros**, direcionado ao crash nativo registrado no diagnóstico.

- Proteção de memória executada pela arquitetura real do processo no MEmu/Houdini.
- Cópia do hook em páginas ARM protegidas com escrita temporária e restauração da proteção.
- Módulo original e bibliotecas sob lib/ preservados; hooks mantidos.
- Código de máquina das bibliotecas do carregador preservado, com redirecionamento de dois imports.
- Impede reutilização de lib.so antigo com o mesmo tamanho.

Baixe **youcine-tv-mod-compat-v2.apk**. Usa a mesma assinatura da compat-v1.
Compilação e integridade conferidas. Não houve execução no aparelho; o teste e a confirmação de funcionamento ficam com o usuário.
