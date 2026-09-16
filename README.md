# Auditoria de Refeições - atualização para a planilha nova

Esta versão foi adaptada para a estrutura `CONFIGURACAO + LANCAMENTOS` da nova planilha de medição.

## O que foi alterado

1. Novo leitor da aba `LANCAMENTOS`.
2. Leitura do período e dos preços na `CONFIGURACAO` por rótulo, sem depender de células fixas.
3. Correção automática de fechamento mensal quando a planilha informar um dia inexistente, como `31-4-26` -> `30/04/2026`.
4. Leitura dinâmica de `COLABORADORES` e `EXCECOES`.
5. Suporte a `TODAS` nas exceções.
6. Suporte a valores diferentes para Café, Almoço e Janta.
7. Glosa financeira calculada pelo valor real do tipo de refeição.
8. Compatibilidade mantida com o layout antigo baseado na aba `REFEIÇÕES`.
9. Testes automatizados adicionados para o layout novo.

## Execução

1. Rode `INSTALAR_AMBIENTE.bat` para preparar o ambiente.
2. Rode `EXECUTAR_RESTAURANTE.bat` para iniciar o sistema.
3. Acesse `http://127.0.0.1:8000`.

## Testes

```bat
venv\Scripts\python.exe -m unittest discover -s tests -v
```
