from datetime import date, datetime, time
from decimal import Decimal

from app.config.settings import (
    ACAO_DESCONTAR_VALE,
    HORARIO_ALMOCO_FIM,
    HORARIO_ALMOCO_INICIO,
    HORARIO_CAFE_FIM,
    HORARIO_CAFE_INICIO,
    HORARIO_CAFE_MAXIMO,
    HORARIO_JANTA_FIM,
    HORARIO_JANTA_INICIO,
    HORARIO_JANTA_MINIMO,
    TOLERANCIA_ASSINATURA_MINUTOS,
    TOLERANCIA_VALOR,
)
from app.utils.helpers import (
    ajustar_horario,
    format_date,
    format_time,
    limpar_mojibake,
    normalizar_texto,
    normalizar_tipo_refeicao,
)


def _to_decimal(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except Exception:
        return None


def _valor_refeicao(ref: dict) -> Decimal | None:
    total = _to_decimal(ref.get('valor_total'))
    if total is not None:
        return total
    unitario = _to_decimal(ref.get('valor_unitario'))
    if unitario is None:
        return None
    return unitario * Decimal(ref.get('quantidade', 1) or 1)


def validar_autorizacao_refeicao(autorizacoes: list, matricula: int, data_refeicao, tipo_refeicao: str) -> dict:
    tipo_norm = normalizar_tipo_refeicao(tipo_refeicao)

    if not tipo_norm:
        return {
            "encontrou": False,
            "status": "PENDENTE",
            "autorizado": None,
            "motivo": "Tipo de refeição inválido ou não reconhecido."
        }

    tipo_ref = tipo_norm[0]
    regras_colaborador = [a for a in autorizacoes if a.get("matricula") == matricula]

    if not regras_colaborador:
        return {
            "encontrou": False,
            "status": "SEM_AUTORIZACAO",
            "autorizado": None,
            "motivo": "Sem autorização específica cadastrada. Aplicar regra normal pelo cartão de ponto."
        }

    regras_mesmo_tipo = [a for a in regras_colaborador if tipo_ref in a.get("tipos", [])]
    if not regras_mesmo_tipo:
        return {
            "encontrou": True,
            "status": "TIPO_NAO_AUTORIZADO",
            "autorizado": False,
            "motivo": "Colaborador possui autorização cadastrada, mas não para este tipo de refeição."
        }

    for regra in regras_mesmo_tipo:
        if not regra.get("valido", True):
            return {
                "encontrou": True,
                "status": "AUTORIZACAO_INVALIDA",
                "autorizado": None,
                "motivo": "Autorização encontrada, mas possui data ou campo obrigatório inválido."
            }

        data_inicio = regra.get("data_inicio")
        data_fim = regra.get("data_fim")
        if data_inicio <= data_refeicao <= data_fim:
            if regra.get("autorizado") is True:
                return {
                    "encontrou": True,
                    "status": "AUTORIZADO",
                    "autorizado": True,
                    "motivo": regra.get("motivo") or "Autorizado conforme aba de autorizações."
                }

            if regra.get("autorizado") is False:
                return {
                    "encontrou": True,
                    "status": "NAO_AUTORIZADO",
                    "autorizado": False,
                    "motivo": regra.get("motivo") or "Não autorizado conforme aba de autorizações."
                }

            return {
                "encontrou": True,
                "status": "AUTORIZACAO_PENDENTE",
                "autorizado": None,
                "motivo": "Autorização encontrada, mas campo AUTORIZADO está vazio ou inválido."
            }

    return {
        "encontrou": True,
        "status": "FORA_DO_PERIODO",
        "autorizado": False,
        "motivo": "Assinatura fora do período autorizado. Descontar na próxima recarga do vale."
    }


def status_autorizacao_deve_glosar(status: str) -> bool:
    return status in {"NAO_AUTORIZADO"}


def motivo_recebe_cartao_refeicao(motivo: str) -> bool:
    texto = normalizar_texto(limpar_mojibake(motivo))
    return "RECEBE" in texto and "CARTAO" in texto and "REFEI" in texto


def permite_refeicao_fim_semana_cartao(autorizacao: dict, dia_refeicao, tipo_refeicao: str) -> bool:
    if autorizacao.get("status") != "NAO_AUTORIZADO":
        return False
    if not motivo_recebe_cartao_refeicao(autorizacao.get("motivo", "")):
        return False
    if not isinstance(dia_refeicao, date) or dia_refeicao.weekday() not in {5, 6}:
        return False

    tipos = normalizar_tipo_refeicao(tipo_refeicao)
    return bool(set(tipos) & {"ALMOCO", "JANTA"})


def marcacoes_cronologicas(marcacoes: list) -> list[time]:
    """Descarta totais e horas extras que o PDF possa misturar às batidas."""
    resultado = []
    for marcacao in marcacoes:
        if not isinstance(marcacao, time):
            continue
        if resultado and marcacao < resultado[-1]:
            break
        resultado.append(marcacao)
    return resultado


def jornada_sobrepoe_periodo(marcacoes: list, inicio: time, fim: time) -> bool:
    marcacoes_jornada = marcacoes_cronologicas(marcacoes)
    if len(marcacoes_jornada) < 2:
        return False
    return marcacoes_jornada[0] <= fim and marcacoes_jornada[-1] >= inicio


def jornada_permite_refeicao(info_dia: dict, tipo: str) -> tuple[bool, str]:
    status = info_dia.get('status')
    if status == 'feriado':
        return False, "Dia consta como feriado no cartão de ponto."
    if status == 'dsr':
        return False, "Dia consta como DSR no cartão de ponto."
    if status == 'compensado':
        return False, "Dia consta como compensado/folga."
    if status != 'trabalhando':
        return False, "Status do dia não permite refeição."

    entrada = info_dia.get('entrada')
    saida = info_dia.get('saida')
    marcacoes = info_dia.get('marcacoes') or []

    if not marcacoes:
        return False, "Dia sem marcação no cartão de ponto."
    if len(marcacoes) < 2:
        return False, "Marcação incompleta no cartão de ponto."

    tipo_norm = normalizar_tipo_refeicao(tipo)
    tipo_ref = tipo_norm[0] if tipo_norm else normalizar_texto(tipo)
    if tipo_ref == "ALMOCO":
        marcacoes_jornada = marcacoes_cronologicas(marcacoes)
        if len(marcacoes_jornada) < 2:
            return False, "Marcação incompleta no cartão de ponto."
        inicio_tolerado = ajustar_horario(HORARIO_ALMOCO_INICIO, -TOLERANCIA_ASSINATURA_MINUTOS)
        fim_tolerado = ajustar_horario(HORARIO_ALMOCO_FIM, TOLERANCIA_ASSINATURA_MINUTOS)
        contem_almoco = jornada_sobrepoe_periodo(marcacoes, inicio_tolerado, fim_tolerado)
        if contem_almoco:
            return True, f"Colaborador trabalhou no período do almoço, considerando tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."
        return False, f"Jornada não contempla o período do almoço, mesmo com tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."

    if tipo_ref == "JANTA":
        inicio_tolerado = ajustar_horario(HORARIO_JANTA_INICIO, -TOLERANCIA_ASSINATURA_MINUTOS)
        fim_tolerado = ajustar_horario(HORARIO_JANTA_FIM, TOLERANCIA_ASSINATURA_MINUTOS)
        limite_janta = ajustar_horario(HORARIO_JANTA_MINIMO, -TOLERANCIA_ASSINATURA_MINUTOS)
        if saida and saida >= limite_janta and jornada_sobrepoe_periodo(marcacoes, inicio_tolerado, fim_tolerado):
            return True, f"Colaborador trabalhou próximo ao horário mínimo de janta, considerando tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."
        return False, f"Janta sem trabalho após horário mínimo, mesmo com tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."

    if tipo_ref == "CAFE":
        inicio_tolerado = ajustar_horario(HORARIO_CAFE_INICIO, -TOLERANCIA_ASSINATURA_MINUTOS)
        fim_tolerado = ajustar_horario(HORARIO_CAFE_FIM, TOLERANCIA_ASSINATURA_MINUTOS)
        limite_cafe = ajustar_horario(HORARIO_CAFE_MAXIMO, TOLERANCIA_ASSINATURA_MINUTOS)
        if entrada and entrada <= limite_cafe and jornada_sobrepoe_periodo(marcacoes, inicio_tolerado, fim_tolerado):
            return True, f"Colaborador iniciou jornada dentro do horário permitido para café, considerando tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."
        return False, f"Café sem entrada dentro da tolerância de {TOLERANCIA_ASSINATURA_MINUTOS} minutos."

    return False, "Tipo de refeição não reconhecido para validação de jornada."


def montar_ocorrencia(ref: dict, status: str, motivo: str, ponto: dict | None = None, info_dia: dict | None = None,
                      origem: str = "REFEIÇÕES", autorizacao: dict | None = None) -> dict:
    dia = ref.get('dia')
    nome = limpar_mojibake(ref.get('nome') or "")
    if ponto:
        nome = nome or limpar_mojibake(ponto.get('nome') or "")

    info_dia = info_dia or {}
    motivo = limpar_mojibake(motivo or "")
    tipo_refeicao = limpar_mojibake(ref.get('tipo') or ref.get('tipo_refeicao') or "")
    autorizacao_motivo = limpar_mojibake((autorizacao or {}).get('motivo', ''))
    return {
        'matricula': ref.get('matricula'),
        'nome': nome,
        'data': format_date(dia),
        'dia': format_date(dia),
        'dia_semana': (info_dia.get('dia_semana') or ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM'][dia.weekday()]) if isinstance(dia, date) else "",
        'tipo_refeicao': tipo_refeicao,
        'status': status,
        'motivo': motivo,
        'descricao': motivo,
        'entrada': format_time(info_dia.get('entrada')),
        'saida_almoco': format_time(info_dia.get('saida_almoco')),
        'retorno_almoco': format_time(info_dia.get('retorno_almoco')),
        'saida': format_time(info_dia.get('saida')),
        'total_trabalhado': format_time(info_dia.get('total_trabalhado')),
        'origem': origem,
        'linha_excel': ref.get('linha_excel'),
        'numero_controle': ref.get('numero_controle', ''),
        'quantidade': ref.get('quantidade', 1),
        'valor_unitario': float(_to_decimal(ref.get('valor_unitario'))) if _to_decimal(ref.get('valor_unitario')) is not None else None,
        'valor_total_refeicao': float(_valor_refeicao(ref)) if _valor_refeicao(ref) is not None else None,
        'autorizacao_status': (autorizacao or {}).get('status', ''),
        'autorizacao_motivo': autorizacao_motivo,
        'acao_recomendada': ACAO_DESCONTAR_VALE if status == "GLOSA" else ""
    }


def auditar(refeicoes_data: dict, pontos_por_matricula: dict) -> list:
    ocorrencias = []
    refeicoes = refeicoes_data['refeicoes']
    excecoes = refeicoes_data['excecoes']
    periodo_excel_inicio = refeicoes_data['periodo_inicio']
    periodo_excel_fim = refeicoes_data['periodo_fim']
    total_refeicoes_calculado = sum(ref.get('quantidade', 1) for ref in refeicoes)

    chaves_exatas = {}
    duplicidades_alertadas = set()

    for ref in refeicoes:
        chave = (ref['matricula'], ref['tipo'], ref['dia'])
        chaves_exatas[chave] = chaves_exatas.get(chave, 0) + ref.get('quantidade', 1)

    totais_planilha = refeicoes_data.get('totais_planilha', {})
    total_mensal_informado = totais_planilha.get('total_mensal_refeicoes')
    if total_mensal_informado is not None and total_mensal_informado != total_refeicoes_calculado:
        ocorrencias.append(montar_ocorrencia({
            'matricula': None,
            'nome': '',
            'tipo': '',
            'dia': periodo_excel_inicio
        }, "DIVERGÊNCIA", f"Total mensal de refeições informado ({total_mensal_informado}) não confere com a contagem dos dias preenchidos ({total_refeicoes_calculado}).", origem="VALIDAÇÃO_FINANCEIRA"))

    for divergencia_dia in totais_planilha.get('total_diario_divergencias', []):
        ocorrencias.append(montar_ocorrencia({
            'matricula': None,
            'nome': '',
            'tipo': '',
            'dia': date(periodo_excel_inicio.year, periodo_excel_inicio.month, divergencia_dia['dia']),
            'linha_excel': divergencia_dia.get('linha_excel')
        }, "DIVERGÊNCIA", f"Total diário informado ({divergencia_dia['informado']}) não confere com a contagem do dia ({divergencia_dia['calculado']}).", origem="VALIDAÇÃO_TOTAL_DIÁRIO"))

    valor_unitario_planilha = totais_planilha.get('valor_unitario')
    valores_por_tipo = totais_planilha.get('valores_unitarios_por_tipo') or {}
    valor_total_planilha = totais_planilha.get('valor_total')
    if valor_unitario_planilha is None and not valores_por_tipo:
        ocorrencias.append(montar_ocorrencia({
            'matricula': None,
            'nome': '',
            'tipo': '',
            'dia': periodo_excel_inicio
        }, "ALERTA", "Valor unitário de refeição não encontrado no fechamento financeiro da planilha.", origem="VALIDAÇÃO_FINANCEIRA"))

    if valor_total_planilha is not None:
        valores_refs = [_valor_refeicao(ref) for ref in refeicoes]
        if valores_refs and all(v is not None for v in valores_refs):
            valor_total_calculado = sum(valores_refs, Decimal('0'))
        elif valor_unitario_planilha is not None:
            valor_total_calculado = Decimal(total_refeicoes_calculado) * _to_decimal(valor_unitario_planilha)
        else:
            valor_total_calculado = None

        if valor_total_calculado is not None and abs(valor_total_calculado - _to_decimal(valor_total_planilha)) > TOLERANCIA_VALOR:
            from app.services.relatorio_service import dinheiro
            ocorrencias.append(montar_ocorrencia({
                'matricula': None,
                'nome': '',
                'tipo': '',
                'dia': periodo_excel_inicio
            }, "DIVERGÊNCIA", f"Valor total financeiro informado ({dinheiro(valor_total_planilha)}) não confere com o valor calculado dos lançamentos ({dinheiro(valor_total_calculado)}).", origem="VALIDAÇÃO_FINANCEIRA"))

    for linha in refeicoes_data.get('linhas_refeicoes', []):
        total_inf = linha.get('total_informado')
        if total_inf is not None and total_inf != linha['total_calculado']:
            ocorrencias.append(montar_ocorrencia({
                'matricula': linha['matricula'],
                'nome': linha['nome'],
                'tipo': linha['tipo'],
                'dia': periodo_excel_inicio,
                'linha_excel': linha['linha_excel']
            }, "DIVERGÊNCIA", "Total informado não confere com soma dos dias.", origem="VALIDAÇÃO_TOTAL"))

        valor_unit = linha.get('valor_unitario')
        valor_total = linha.get('valor_total_informado')
        if valor_unit is None and valor_total is not None:
            ocorrencias.append(montar_ocorrencia({
                'matricula': linha['matricula'],
                'nome': linha['nome'],
                'tipo': linha['tipo'],
                'dia': periodo_excel_inicio,
                'linha_excel': linha['linha_excel']
            }, "ALERTA", "Valor unitário ausente.", origem="VALIDAÇÃO_VALOR"))
        elif valor_unit is not None and valor_total is not None:
            calculado = valor_unit * Decimal(linha['total_calculado'])
            if abs(calculado - valor_total) > TOLERANCIA_VALOR:
                ocorrencias.append(montar_ocorrencia({
                    'matricula': linha['matricula'],
                    'nome': linha['nome'],
                    'tipo': linha['tipo'],
                    'dia': periodo_excel_inicio,
                    'linha_excel': linha['linha_excel']
                }, "DIVERGÊNCIA", "Valor total não confere com valor unitário.", origem="VALIDAÇÃO_VALOR"))

        nome_cadastro = refeicoes_data['colaboradores'].get(linha['matricula'])
        if nome_cadastro is None:
            ocorrencias.append(montar_ocorrencia({
                'matricula': linha['matricula'],
                'nome': linha['nome'],
                'tipo': linha['tipo'],
                'dia': periodo_excel_inicio,
                'linha_excel': linha['linha_excel']
            }, "ALERTA", "Matrícula na medição não localizada na aba COLABORADORES.", origem="COLABORADORES"))
        elif linha['nome'] and normalizar_texto(linha['nome']) != normalizar_texto(nome_cadastro):
            ocorrencias.append(montar_ocorrencia({
                'matricula': linha['matricula'],
                'nome': linha['nome'],
                'tipo': linha['tipo'],
                'dia': periodo_excel_inicio,
                'linha_excel': linha['linha_excel']
            }, "ALERTA", "Nome divergente entre LANCAMENTOS e COLABORADORES.", origem="COLABORADORES"))

    for ref in refeicoes:
        matricula = ref['matricula']
        dia = ref['dia']
        tipo = ref['tipo']
        ponto = pontos_por_matricula.get(matricula)
        chave = (matricula, tipo, dia)

        if chaves_exatas[chave] > 1 and chave not in duplicidades_alertadas and not duplicidades_alertadas.add(chave):
            ocorrencias.append(montar_ocorrencia(ref, "DIVERGÊNCIA", "Duplicidade: mesma refeição lançada mais de uma vez.", ponto, origem="DUPLICIDADE"))

        if not (periodo_excel_inicio <= dia <= periodo_excel_fim):
            ocorrencias.append(montar_ocorrencia(ref, "DIVERGÊNCIA", "Refeição lançada fora do período de medição.", ponto))
            continue

        aut = validar_autorizacao_refeicao(
            autorizacoes=excecoes,
            matricula=matricula,
            data_refeicao=dia,
            tipo_refeicao=tipo
        )
        regra_cartao_fim_semana = permite_refeicao_fim_semana_cartao(aut, dia, tipo)

        if aut["status"] == "AUTORIZADO":
            ocorrencias.append(montar_ocorrencia(
                ref,
                "OK",
                f"Refeição válida por autorização: {aut['motivo']}",
                ponto,
                autorizacao=aut
            ))
            continue

        if status_autorizacao_deve_glosar(aut["status"]) and not regra_cartao_fim_semana:
            ocorrencias.append(montar_ocorrencia(ref, "GLOSA", aut["motivo"], ponto, autorizacao=aut))
            continue

        if not ponto:
            ocorrencias.append(montar_ocorrencia(ref, "GLOSA", "Colaborador possui refeição na planilha, mas não possui cartão de ponto enviado.", autorizacao=aut))
            continue

        if normalizar_texto(ref.get('nome')) and normalizar_texto(ponto.get('nome')) and normalizar_texto(ref.get('nome')) != normalizar_texto(ponto.get('nome')):
            ocorrencias.append(montar_ocorrencia(ref, "ALERTA", "Nome divergente entre planilha e cartão de ponto.", ponto, origem="IDENTIFICAÇÃO"))

        if not (ponto['periodo_inicio'] <= dia <= ponto['periodo_fim']):
            ocorrencias.append(montar_ocorrencia(ref, "PENDENTE", "Refeição fora do período do cartão de ponto.", ponto, autorizacao=aut))
            continue

        info_dia = ponto['dias'].get(dia)
        if not info_dia:
            ocorrencias.append(montar_ocorrencia(ref, "PENDENTE", "Dia não encontrado no cartão de ponto.", ponto, autorizacao=aut))
            continue

        permitido, motivo = jornada_permite_refeicao(info_dia, tipo)
        if permitido:
            if regra_cartao_fim_semana:
                motivo = f"{motivo} Regra de fim de semana aplicada para colaborador que recebe cartão de refeição."
            ocorrencias.append(montar_ocorrencia(ref, "OK", motivo, ponto, info_dia, autorizacao=aut))
            continue

        ocorrencias.append(montar_ocorrencia(ref, "GLOSA", motivo, ponto, info_dia, autorizacao=aut))

    for alerta in refeicoes_data.get('alertas_estrutura', []):
        ocorrencias.append(montar_ocorrencia({
            'matricula': None,
            'nome': '',
            'tipo': '',
            'dia': periodo_excel_inicio
        }, "ALERTA", alerta, origem="ESTRUTURA"))

    ocorrencias.sort(key=lambda x: (
        datetime.strptime(x['data'], '%d/%m/%Y') if x.get('data') else datetime.max,
        str(x.get('matricula') or ''),
        x.get('tipo_refeicao') or '',
        x.get('origem') or ''
    ))
    return ocorrencias


def calcular_financeiro(refeicoes_data: dict, ocorrencias: list) -> dict:
    """Consolida financeiro aceitando valor único ou preços diferentes por refeição."""
    totais_planilha = refeicoes_data.get('totais_planilha', {})
    refeicoes = refeicoes_data.get('refeicoes', [])
    linhas = refeicoes_data.get('linhas_refeicoes', [])

    total_refeicoes = sum(ref.get('quantidade', 1) for ref in refeicoes)
    total_mensal_informado = totais_planilha.get('total_mensal_refeicoes')
    valor_total_informado = _to_decimal(totais_planilha.get('valor_total'))

    valores_por_tipo_raw = totais_planilha.get('valores_unitarios_por_tipo') or {}
    valores_por_tipo = {
        chave: float(_to_decimal(valor))
        for chave, valor in valores_por_tipo_raw.items()
        if _to_decimal(valor) is not None
    }

    valores_unitarios = []
    for linha in linhas:
        dec = _to_decimal(linha.get('valor_unitario'))
        if dec is not None:
            valores_unitarios.append(dec)
    for valor in valores_por_tipo_raw.values():
        dec = _to_decimal(valor)
        if dec is not None:
            valores_unitarios.append(dec)

    unicos = sorted(set(valores_unitarios))
    valor_unitario_planilha = _to_decimal(totais_planilha.get('valor_unitario'))
    valor_unitario = valor_unitario_planilha if valor_unitario_planilha is not None else (unicos[0] if len(unicos) == 1 else None)
    valor_unitario_variavel = len(unicos) > 1

    valores_refs = [_valor_refeicao(ref) for ref in refeicoes]
    if valores_refs and all(v is not None for v in valores_refs):
        total_provisionado_calculado = sum(valores_refs, Decimal('0'))
    elif valor_unitario is not None:
        total_provisionado_calculado = Decimal(total_refeicoes) * valor_unitario
    else:
        total_provisionado_calculado = Decimal('0')

    total_linhas_informado = sum(
        (_to_decimal(linha.get('valor_total_informado')) or Decimal('0'))
        for linha in linhas
    )
    total_provisionado = valor_total_informado if valor_total_informado is not None else (
        total_linhas_informado if total_linhas_informado else total_provisionado_calculado
    )

    glosa_recomendada = Decimal('0')
    glosas_quantidade = 0
    for ocorrencia in ocorrencias:
        if ocorrencia.get('status') != 'GLOSA':
            continue
        glosas_quantidade += int(ocorrencia.get('quantidade', 1) or 1)
        valor_ocorrencia = _to_decimal(ocorrencia.get('valor_total_refeicao'))
        if valor_ocorrencia is not None:
            glosa_recomendada += valor_ocorrencia
        elif valor_unitario is not None:
            glosa_recomendada += valor_unitario * Decimal(ocorrencia.get('quantidade', 1) or 1)

    total_conforme = max(total_provisionado_calculado - glosa_recomendada, Decimal('0'))
    divergencia = total_provisionado - total_conforme if total_provisionado else glosa_recomendada
    diferenca_fechamento = (
        valor_total_informado - total_provisionado_calculado
        if valor_total_informado is not None
        else Decimal('0')
    )

    return {
        'valor_unitario': float(valor_unitario) if valor_unitario is not None else None,
        'valor_unitario_variavel': valor_unitario_variavel,
        'valores_unitarios_por_tipo': valores_por_tipo,
        'total_refeicoes_calculado': total_refeicoes,
        'total_refeicoes_informado': total_mensal_informado,
        'valor_total_informado': float(valor_total_informado) if valor_total_informado is not None else None,
        'total_provisionado_calculado': float(total_provisionado_calculado),
        'total_provisionado': float(total_provisionado),
        'total_conforme': float(total_conforme),
        'divergencia': float(divergencia),
        'diferenca_fechamento': float(diferenca_fechamento),
        'glosa_recomendada': float(glosa_recomendada),
        'glosas_quantidade': glosas_quantidade,
        'fechamento_ok': abs(diferenca_fechamento) <= TOLERANCIA_VALOR
    }

