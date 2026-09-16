# Mapeamento do Sistema de Auditoria de Refeições

## Visão Geral

O sistema audita refeições lançadas em planilha Excel contra cartões de ponto em PDF. A aplicação recebe arquivos via Flask, extrai dados, aplica regras de autorização/jornada, calcula financeiro e gera relatórios em Excel/PDF.

## Funções Encontradas

### normalizar_texto(valor)
- Parâmetros: `valor`
- Retorno: texto em maiúsculo, sem acentos e com espaços normalizados.
- Quem chama: parsers, regras de autorização, validações.
- Quem utiliza: Excel, auditoria e helpers de busca textual.
- Responsabilidade: padronizar texto para comparação.

### parse_date_value(valor)
- Parâmetros: `valor`
- Retorno: `date` ou `None`.
- Quem chama: parser Excel.
- Quem utiliza: leitura de período e exceções.
- Responsabilidade: converter datas de célula/string.

### parse_money(valor)
- Parâmetros: `valor`
- Retorno: `Decimal` ou `None`.
- Quem chama: parser Excel, financeiro, relatório.
- Quem utiliza: consolidação financeira.
- Responsabilidade: converter valores monetários.

### first_value_after(row, start_idx, predicate)
- Parâmetros: linha, índice inicial, predicado.
- Retorno: primeiro valor posterior que atende ao predicado.
- Quem chama: helpers de leitura da planilha.
- Quem utiliza: parser Excel.
- Responsabilidade: localizar dados em linhas de cabeçalho/rodapé.

### first_money_after(row, start_idx)
- Parâmetros: linha, índice inicial.
- Retorno: primeiro valor monetário posterior.
- Quem chama: parser Excel.
- Quem utiliza: fechamento financeiro.
- Responsabilidade: extrair totais financeiros no rodapé.

### first_text_after(row, start_idx)
- Parâmetros: linha, índice inicial.
- Retorno: primeiro texto posterior.
- Quem chama: parser Excel.
- Quem utiliza: dados do restaurante.
- Responsabilidade: extrair razão social, CNPJ e cidade.

### is_marcacao_refeicao(valor)
- Parâmetros: `valor`
- Retorno: booleano.
- Quem chama: parser Excel.
- Quem utiliza: contagem de refeições por dia.
- Responsabilidade: identificar marcações válidas na planilha.

### format_date(d)
- Parâmetros: `d`
- Retorno: data formatada `dd/mm/aaaa`.
- Quem chama: rotas, auditoria.
- Quem utiliza: JSON e relatório.
- Responsabilidade: saída legível de datas.

### format_time(t)
- Parâmetros: `t`
- Retorno: horário `HH:MM`.
- Quem chama: auditoria.
- Quem utiliza: ocorrências.
- Responsabilidade: saída legível de horas.

### ajustar_horario(t, minutos)
- Parâmetros: horário e quantidade de minutos.
- Retorno: horário ajustado.
- Quem chama: regra de jornada.
- Quem utiliza: tolerância de assinatura.
- Responsabilidade: aplicar margem antes/depois do ponto.

### tipo_refeicao_norm(valor)
- Parâmetros: `valor`
- Retorno: tipo textual normalizado para exibição.
- Quem chama: parser Excel.
- Quem utiliza: ocorrências e relatório.
- Responsabilidade: padronizar nomes de refeição.

### normalizar_tipo_refeicao(valor)
- Parâmetros: `valor`
- Retorno: lista com tipos internos: `ALMOCO`, `JANTA`, `CAFE`.
- Quem chama: exceções, auditoria, regra de fim de semana.
- Quem utiliza: validação de autorização.
- Responsabilidade: interpretar tipos compostos.

### normalizar_autorizado(valor)
- Parâmetros: `valor`
- Retorno: `True`, `False` ou `None`.
- Quem chama: parser Excel.
- Quem utiliza: aba de exceções/autorização.
- Responsabilidade: converter S/N.

### parse_texto_cartao_ponto(full_text)
- Parâmetros: texto extraído de um cartão.
- Retorno: dicionário de ponto por colaborador.
- Quem chama: parser PDF.
- Quem utiliza: auditoria de jornada.
- Responsabilidade: extrair matrícula, nome, período, dias e batidas.

### parse_pdf_ponto(pdf_bytes)
- Parâmetros: bytes do PDF.
- Retorno: primeiro cartão encontrado.
- Quem chama: compatibilidade.
- Quem utiliza: usos legados.
- Responsabilidade: manter API anterior.

### parse_pdf_pontos(pdf_bytes)
- Parâmetros: bytes do PDF.
- Retorno: `{matricula: ponto}`.
- Quem chama: rota `/api/analisar`.
- Quem utiliza: auditoria.
- Responsabilidade: processar PDF com múltiplos cartões.

### parse_excel_refeicoes(xlsx_bytes)
- Parâmetros: bytes do Excel.
- Retorno: dicionário com refeições, exceções, colaboradores, restaurante e totais.
- Quem chama: rota `/api/analisar`.
- Quem utiliza: auditoria e financeiro.
- Responsabilidade: extrair dados da medição.

### validar_autorizacao_refeicao(autorizacoes, matricula, data_refeicao, tipo_refeicao)
- Parâmetros: lista de autorizações, matrícula, data, tipo.
- Retorno: dicionário de status.
- Quem chama: `auditar`.
- Quem utiliza: regra de autorização.
- Responsabilidade: aplicar aba de exceções.

### status_autorizacao_deve_glosar(status)
- Parâmetros: status da autorização.
- Retorno: booleano.
- Quem chama: `auditar`.
- Quem utiliza: fluxo de glosa.
- Responsabilidade: indicar autorização que gera glosa imediata.

### motivo_recebe_cartao_refeicao(motivo)
- Parâmetros: motivo textual.
- Retorno: booleano.
- Quem chama: regra de fim de semana.
- Quem utiliza: autorização negativa por cartão.
- Responsabilidade: detectar colaboradores que recebem cartão.

### permite_refeicao_fim_semana_cartao(autorizacao, dia_refeicao, tipo_refeicao)
- Parâmetros: autorização, data, tipo.
- Retorno: booleano.
- Quem chama: `auditar`.
- Quem utiliza: exceção de sábado/domingo.
- Responsabilidade: liberar almoço/janta no fim de semana se houver ponto.

### jornada_permite_refeicao(info_dia, tipo)
- Parâmetros: informações do dia e tipo.
- Retorno: `(permitido, motivo)`.
- Quem chama: `auditar`.
- Quem utiliza: validação contra cartão de ponto.
- Responsabilidade: aplicar regras de café, almoço, janta e tolerância.

### montar_ocorrencia(ref, status, motivo, ponto, info_dia, origem, autorizacao)
- Parâmetros: referência da refeição, status, motivo e dados auxiliares.
- Retorno: dicionário de ocorrência.
- Quem chama: `auditar`.
- Quem utiliza: JSON e relatórios.
- Responsabilidade: padronizar ocorrências.

### auditar(refeicoes_data, pontos_por_matricula)
- Parâmetros: dados da planilha e cartões de ponto.
- Retorno: lista de ocorrências.
- Quem chama: rota `/api/analisar`.
- Quem utiliza: relatórios e financeiro.
- Responsabilidade: motor principal de auditoria.

### calcular_financeiro(refeicoes_data, ocorrencias)
- Parâmetros: dados da planilha e ocorrências.
- Retorno: dicionário financeiro.
- Quem chama: rota `/api/analisar`.
- Quem utiliza: PDF e tela.
- Responsabilidade: consolidar contagem, valores, fechamento e glosa.

### dinheiro(valor)
- Parâmetros: valor monetário.
- Retorno: string `R$`.
- Quem chama: relatório e validações.
- Quem utiliza: PDF.
- Responsabilidade: formatar valores.

### resultado_pdf(status)
- Parâmetros: status.
- Retorno: rótulo para PDF.
- Quem chama: relatório.
- Quem utiliza: tabelas PDF.
- Responsabilidade: traduzir status para resultado.

### gerar_pdf_auditoria(data)
- Parâmetros: payload da auditoria.
- Retorno: `BytesIO`.
- Quem chama: rota `/api/exportar_pdf`.
- Quem utiliza: download PDF.
- Responsabilidade: gerar relatório consolidado em PDF.

### dataParaOrdenacao_py(valor)
- Parâmetros: string de data.
- Retorno: `datetime`.
- Quem chama: relatório.
- Quem utiliza: ordenação de ocorrências.
- Responsabilidade: ordenar datas.

### index()
- Parâmetros: nenhum.
- Retorno: `index.html`.
- Quem chama: Flask.
- Quem utiliza: navegador.
- Responsabilidade: servir tela principal.

### analisar()
- Parâmetros: request Flask.
- Retorno: JSON.
- Quem chama: frontend.
- Quem utiliza: tela.
- Responsabilidade: receber uploads e executar auditoria.

### exportar()
- Parâmetros: request Flask.
- Retorno: Excel.
- Quem chama: frontend.
- Quem utiliza: download.
- Responsabilidade: exportar ocorrências em Excel.

### exportar_pdf()
- Parâmetros: request Flask.
- Retorno: PDF.
- Quem chama: frontend.
- Quem utiliza: download.
- Responsabilidade: exportar relatório PDF.

## Domínios Identificados

- Configurações: horários, tolerâncias e ação recomendada.
- Utilitários: normalização, datas, dinheiro, horários.
- Parser Excel: leitura de refeições, exceções, colaboradores, restaurante e financeiro.
- Parser PDF: leitura do cartão de ponto.
- Auditoria: autorizações, jornada, fim de semana, glosas e divergências.
- Relatórios: Excel e PDF.
- Flask: rotas e montagem da aplicação.
