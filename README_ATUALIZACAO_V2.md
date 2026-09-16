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

## Arquivo usado na validação

`MEDIÇÃO_RESTAURANTE_ELMIRAS_PERIODO_01-04-2026_ATE_30-04-2026.xlsx`

Resultado de leitura validado:

- Período: 01/04/2026 a 30/04/2026
- 98 colaboradores cadastrados
- 3 lançamentos encontrados no arquivo enviado
- 3 refeições apuradas
- Café: R$ 9,00
- Almoço: R$ 29,90
- Janta: R$ 29,90
- Total dos lançamentos presentes: R$ 89,70

## Testes

Execute na raiz do projeto:

```bat
venv\Scripts\python.exe -m unittest discover -s tests -v
```

Foram adicionados testes específicos para período mensal, preços variáveis e exceção `TODAS`.
