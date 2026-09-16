# Mapeamento da planilha nova - Auditoria de Refeições v2

## Fonte principal

A aplicação agora reconhece automaticamente o layout baseado nas abas:

- `CONFIGURACAO`
- `COLABORADORES`
- `EXCECOES`
- `LANCAMENTOS`

As abas `AUX_CONTROLES`, `CONTROLE_REFEICOES`, `AUDITORIA` e `RESUMO` continuam podendo existir na planilha, mas não são usadas como fonte primária da auditoria. Elas são saídas/apoios do próprio Excel.

## CONFIGURACAO

O leitor procura os rótulos, e não posições fixas de célula:

- Data inicial da medição
- Data final da medição
- Café
- Almoço
- Janta

A data final `31-4-26`, presente no arquivo de abril usado na atualização, é interpretada como o último dia real do mês: `30/04/2026`.

## COLABORADORES

O cabeçalho é detectado pela presença de:

- MATRÍCULA
- COLABORADOR ou NOME

A posição da linha do cabeçalho pode mudar sem quebrar o leitor.

## LANCAMENTOS

É a nova fonte oficial das refeições. O cabeçalho é detectado pelos campos:

- Nº CONTROLE
- DATA
- MATRÍCULA
- COLABORADOR
- TIPO
- QUANTIDADE
- VALOR UNIT.
- TOTAL

O programa utiliza os dados digitados e, quando fórmulas do Excel não tiverem valor armazenado, consegue obter nome pelo cadastro e preço pela aba `CONFIGURACAO`.

## EXCECOES

O cabeçalho é detectado pelos campos:

- MATRÍCULA
- COLABORADOR
- INÍCIO
- FIM
- REFEIÇÃO
- MOTIVO
- AUTORIZADO
- RESPONSÁVEL
- STATUS

`TODAS` é convertido internamente para Café + Almoço + Janta.

Registros com status `INATIVA`, `INATIVO`, `CANCELADA` ou `CANCELADO` não são considerados autorizações válidas.

## Financeiro

A versão antiga partia do pressuposto de um único valor unitário. A versão nova aceita preços independentes para:

- Café
- Almoço
- Janta

Glosas e total conforme passam a usar o valor real do tipo de refeição auditado.

## Compatibilidade

O leitor antigo da aba `REFEIÇÕES` foi mantido como fallback. Assim, arquivos antigos continuam aceitos enquanto o layout novo é priorizado.
