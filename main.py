"""Entrada compatível do Sistema de Auditoria de Refeições."""

from app.app import app, create_app
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
from app.parsers.excel_parser import parse_excel_refeicoes
from app.parsers.pdf_parser import parse_pdf_ponto, parse_pdf_pontos, parse_texto_cartao_ponto
from app.routes import analisar, exportar, exportar_pdf, index
from app.services.auditoria_service import (
    auditar,
    calcular_financeiro,
    jornada_permite_refeicao,
    montar_ocorrencia,
    motivo_recebe_cartao_refeicao,
    permite_refeicao_fim_semana_cartao,
    status_autorizacao_deve_glosar,
    validar_autorizacao_refeicao,
)
from app.services.relatorio_service import (
    dataParaOrdenacao_py,
    dinheiro,
    gerar_pdf_auditoria,
    resultado_pdf,
)
from app.utils.helpers import (
    ajustar_horario,
    first_money_after,
    first_text_after,
    first_value_after,
    format_date,
    format_time,
    is_marcacao_refeicao,
    normalizar_autorizado,
    normalizar_texto,
    normalizar_tipo_refeicao,
    parse_date_value,
    parse_money,
    tipo_refeicao_norm,
)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False, use_reloader=False)
