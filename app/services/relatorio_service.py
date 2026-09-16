import io
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.utils.helpers import limpar_mojibake, limpar_textos, parse_money


def dinheiro(valor) -> str:
    dec = parse_money(valor) or Decimal("0")
    return f"R$ {dec:,.2f}"


def resultado_pdf(status: str) -> str:
    status = limpar_mojibake(status or "")
    if status == "OK":
        return "CONFORME"
    if status == "EXCEÇÃO":
        return "CONFORME (EXCEÇÃO)"
    if status == "GLOSA":
        return "INCONFORME"
    if status in {"ALERTA", "PENDENTE", "DIVERGÊNCIA"}:
        return status
    return status or ""


def dataParaOrdenacao_py(valor):
    try:
        return datetime.strptime(valor or "", "%d/%m/%Y")
    except ValueError:
        return datetime.max


def gerar_pdf_auditoria(data: dict) -> io.BytesIO:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def registrar_fontes_pdf():
        fontes = [
            (
                "AuditSans",
                "AuditSans-Bold",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf",
            ),
            (
                "AuditSans",
                "AuditSans-Bold",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibrib.ttf",
            ),
        ]
        for regular_nome, bold_nome, regular_path, bold_path in fontes:
            if regular_path.exists() and bold_path.exists():
                if regular_nome not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(regular_nome, str(regular_path)))
                if bold_nome not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(bold_nome, str(bold_path)))
                pdfmetrics.registerFontFamily(
                    regular_nome,
                    normal=regular_nome,
                    bold=bold_nome,
                    italic=regular_nome,
                    boldItalic=bold_nome,
                )
                return regular_nome, bold_nome
        return "Helvetica", "Helvetica-Bold"

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.55 * cm,
        leftMargin=1.55 * cm,
        topMargin=1.15 * cm,
        bottomMargin=1.35 * cm
    )

    navy = colors.HexColor("#1b2746")
    blue = colors.HexColor("#2f5597")
    header_fill = colors.HexColor("#d7e1f2")
    light_blue = colors.HexColor("#edf4fb")
    grid = colors.HexColor("#c9d3e3")
    text_dark = colors.HexColor("#1b2746")
    green_row = colors.HexColor("#e5f2e5")
    yellow_row = colors.HexColor("#ffefaa")
    red_row = colors.HexColor("#f8c1ca")
    white = colors.white
    font_regular, font_bold = registrar_fontes_pdf()

    styles = getSampleStyleSheet()
    title = ParagraphStyle('TitleAudit', parent=styles['Heading1'], alignment=TA_CENTER, fontName=font_bold, fontSize=16, leading=19, textColor=text_dark, spaceAfter=6)
    subtitle = ParagraphStyle('SubtitleAudit', parent=styles['Normal'], fontName=font_regular, alignment=TA_CENTER, fontSize=8.5, leading=11, textColor=colors.HexColor("#667085"), spaceAfter=2)
    section_text = ParagraphStyle('SectionTextAudit', parent=styles['Normal'], fontName=font_bold, fontSize=10.5, leading=12, textColor=white)
    small = ParagraphStyle('SmallAudit', parent=styles['Normal'], fontName=font_regular, fontSize=6.2, leading=7.4)
    normal = ParagraphStyle('NormalAudit', parent=styles['Normal'], fontName=font_regular, fontSize=7.5, leading=9, textColor=colors.HexColor("#111827"))
    meta = ParagraphStyle('MetaAudit', parent=normal, fontName=font_bold, textColor=text_dark)

    data = limpar_textos(data)

    def p(text, style=small):
        texto = limpar_mojibake(str(text or ""))
        return Paragraph(texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)

    def texto_celula(text, padrao="-"):
        texto = limpar_mojibake(str(text or "").strip())
        return texto if texto else padrao

    def descricao_relatorio(o: dict) -> str:
        descricao = limpar_mojibake(o.get('descricao') or o.get('motivo') or '')
        acao = limpar_mojibake(o.get('acao_recomendada') or '')
        if acao:
            return f"{descricao} | Ação recomendada: {acao}"
        return descricao

    def section_bar(text):
        table = Table([[Paragraph(text, section_text)]], colWidths=[doc.width])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), navy),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return table

    def make_table(rows, widths=None, header=True, font_size=6.5, header_fill_color=navy, body_fill=None):
        table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ('FONTNAME', (0, 0), (-1, -1), font_regular),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('GRID', (0, 0), (-1, -1), 0.25, grid),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if body_fill:
            style.append(('BACKGROUND', (0, 1 if header else 0), (-1, -1), body_fill))
        if header:
            style.extend([
                ('BACKGROUND', (0, 0), (-1, 0), header_fill_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), font_bold),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ])
        table.setStyle(TableStyle(style))
        return table

    def row_color(status):
        resultado = resultado_pdf(status)
        if resultado == "CONFORME":
            return green_row
        if resultado == "CONFORME (EXCEÇÃO)":
            return yellow_row
        if resultado == "INCONFORME":
            return red_row
        return yellow_row

    def add_status_row_colors(table, rows, status_index, start_row=1):
        style = []
        for idx, row in enumerate(rows[start_row:], start=start_row):
            style.append(('BACKGROUND', (0, idx), (-1, idx), row_color(row[status_index])))
        table.setStyle(TableStyle(style))
        return table

    ocorrencias = data.get('ocorrencias', [])
    resumo = data.get('resumo', {})
    financeiro = data.get('financeiro', {})
    periodo_excel = data.get('periodo_excel', {})
    restaurante_info = data.get('restaurante_dados') or {}
    restaurante_valor = data.get('restaurante') or restaurante_info or 'CANTINA MINEIRA'
    if isinstance(restaurante_valor, dict):
        restaurante_info = restaurante_valor
        restaurante = limpar_mojibake(restaurante_info.get('nome') or restaurante_info.get('razao_social') or 'CANTINA MINEIRA')
    else:
        restaurante = limpar_mojibake(str(restaurante_valor))
    razao_social = limpar_mojibake(restaurante_info.get('razao_social') or restaurante)
    cnpj = limpar_mojibake(restaurante_info.get('cnpj') or '')
    cidade = limpar_mojibake(restaurante_info.get('cidade') or '')
    gerado_em = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    id_analise = data.get('id_analise') or datetime.now().strftime('%Y%m%d%H%M%S')

    total_refeicoes = resumo.get('total_refeicoes', 0)
    ok = resumo.get('ok', 0)
    excecoes = resumo.get('excecoes', 0)
    glosas = resumo.get('glosas', 0)
    pendencias = resumo.get('alertas', 0) + resumo.get('pendentes', 0) + resumo.get('divergencias', 0)
    conformidade = ((ok + excecoes) / total_refeicoes * 100) if total_refeicoes else 0
    total_ok = max(total_refeicoes - glosas, 0)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d9e2ef"))
        canvas.line(doc_obj.leftMargin, 1.0 * cm, A4[0] - doc_obj.rightMargin, 1.0 * cm)
        canvas.setFont(font_regular, 6.5)
        canvas.setFillColor(colors.HexColor("#98a2b3"))
        canvas.drawCentredString(A4[0] / 2, 0.65 * cm, f"Documento válido para auditoria externa · ID: {id_analise} · {gerado_em} · Sistermi — Auditoria de Refeições v2.0")
        canvas.restoreState()

    story = []
    project_root = Path(__file__).resolve().parents[2]
    logo_path = project_root / "static" / "img" / "logo_sistermi.jpg"
    if os.path.exists(logo_path):
        logo = Image(str(logo_path), width=5.1 * cm, height=1.38 * cm)
        logo.hAlign = 'CENTER'
        story.extend([logo, Spacer(1, 0.28 * cm)])

    story.extend([
        Paragraph("RELATÓRIO CONSOLIDADO DE AUDITORIA — REFEIÇÕES", title),
        Paragraph(f"Restaurante: <b>{restaurante}</b> · Período: <b>{periodo_excel.get('inicio', '')} a {periodo_excel.get('fim', '')}</b>", subtitle),
        Paragraph(f"Razão Social: <b>{razao_social}</b> · CNPJ: <b>{cnpj or '-'}</b> · Cidade: <b>{cidade or '-'}</b>", subtitle),
        Paragraph(f"ID da Análise: {id_analise} · Gerado em: {gerado_em}", subtitle),
        Spacer(1, 0.18 * cm),
        section_bar("RESULTADO DA AUDITORIA"),
        Spacer(1, 0.24 * cm),
    ])

    resultado_rows = [
        ['TOTAL', 'CONFORMES', 'CONF.(EXCEÇÃO)', 'INCONFORMES', 'INC.(EXCEÇÃO)', 'CONFORM.'],
        [total_refeicoes, ok, excecoes, glosas, pendencias, f"{conformidade:.1f}%"]
    ]
    resultado_table = make_table(resultado_rows, widths=[doc.width / 6] * 6, header=True, font_size=7, header_fill_color=header_fill, body_fill=header_fill)
    resultado_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.extend([resultado_table, Spacer(1, 0.45 * cm), section_bar("CONSOLIDADO FINANCEIRO"), Spacer(1, 0.24 * cm)])

    if financeiro.get('valor_unitario_variavel'):
        precos_tipo = financeiro.get('valores_unitarios_por_tipo') or {}
        valor_unitario_pdf = ' / '.join(
            f"{tipo}: {dinheiro(valor)}" for tipo, valor in precos_tipo.items()
        ) or 'VARIÁVEL'
    else:
        valor_unitario_pdf = dinheiro(financeiro.get('valor_unitario'))

    financeiro_rows = [
        ['Ref. Planilha', 'Ref. Apuradas', 'Valor Unitário', 'Valor Informado', 'Valor Calculado', 'Diferença', 'GLOSA RECOMENDADA'],
        [
            financeiro.get('total_refeicoes_informado') if financeiro.get('total_refeicoes_informado') is not None else '-',
            financeiro.get('total_refeicoes_calculado', total_refeicoes),
            p(valor_unitario_pdf),
            dinheiro(financeiro.get('valor_total_informado')),
            dinheiro(financeiro.get('total_provisionado_calculado')),
            dinheiro(financeiro.get('diferenca_fechamento')),
            dinheiro(financeiro.get('glosa_recomendada')),
        ]
    ]
    financeiro_table = make_table(financeiro_rows, widths=[doc.width / 7] * 7, header=True, font_size=6.2, body_fill=colors.HexColor("#eaf4fb"))
    financeiro_table.setStyle(TableStyle([
        ('FONTNAME', (0, 1), (-1, 1), font_bold),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (5, 1), (5, 1), red_row if not financeiro.get('fechamento_ok', True) else colors.HexColor("#eaf4fb")),
        ('BACKGROUND', (-1, 1), (-1, 1), red_row if glosas else colors.HexColor("#eaf4fb")),
    ]))
    status_fechamento = "OK" if financeiro.get('fechamento_ok', True) else "DIVERGENTE"
    story.extend([
        financeiro_table,
        Paragraph(f"Fechamento financeiro: <b>{status_fechamento}</b> · Total conforme após auditoria: <b>{dinheiro(financeiro.get('total_conforme'))}</b> · Divergência/glosa operacional: <b>{dinheiro(financeiro.get('divergencia'))}</b>", subtitle),
        Spacer(1, 0.35 * cm),
        section_bar("RESUMO POR COLABORADOR"),
        Spacer(1, 0.24 * cm)
    ])

    por_colab = {}
    for o in ocorrencias:
        if not o.get('matricula'):
            continue
        item = por_colab.setdefault(o['matricula'], {'nome': o.get('nome', ''), 'total': 0, 'ok': 0, 'excecao': 0, 'glosa': 0, 'revisao': 0, 'ocorrencias': []})
        qtd = int(o.get('quantidade', 1) or 1)
        if o.get('origem') == 'REFEIÇÕES':
            item['total'] += qtd
        if o['status'] == 'OK' and o.get('origem') == 'REFEIÇÕES':
            item['ok'] += qtd
        elif o['status'] == 'EXCEÇÃO' and o.get('origem') == 'REFEIÇÕES':
            item['excecao'] += qtd
        elif o['status'] == 'GLOSA' and o.get('origem') == 'REFEIÇÕES':
            item['glosa'] += qtd
        elif o['status'] in {'ALERTA', 'PENDENTE', 'DIVERGÊNCIA'}:
            item['revisao'] += 1
        item['ocorrencias'].append(o)

    resumo_rows = [['MATRÍC.', 'NOME', 'TOTAL', 'CONF.', 'CONF.(EXC.)', 'INC.', 'INC.(EXC.)', 'TOTAL OK', '% CONF.']]
    for mat, item in sorted(por_colab.items(), key=lambda kv: str(kv[0])):
        base = item['total'] or len(item['ocorrencias'])
        pct = ((item['ok'] + item['excecao']) / base * 100) if base else 0
        resumo_rows.append([mat, p(item['nome']), base, item['ok'], item['excecao'], item['glosa'], item['revisao'], item['ok'] + item['excecao'], f"{pct:.1f}%"])

    resumo_rows.append(['', p('TOTAL GERAL', meta), total_refeicoes, ok, excecoes, glosas, pendencias, total_ok, f"{conformidade:.1f}%"])
    resumo_table = make_table(resumo_rows, widths=[1.35*cm, 4.85*cm, 1.15*cm, 1.15*cm, 1.5*cm, 0.95*cm, 1.55*cm, 1.35*cm, 1.35*cm], header=True, font_size=6.15)
    resumo_style = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('BACKGROUND', (0, len(resumo_rows) - 1), (-1, len(resumo_rows) - 1), header_fill),
        ('FONTNAME', (0, len(resumo_rows) - 1), (-1, len(resumo_rows) - 1), font_bold),
    ]
    for idx, row in enumerate(resumo_rows[1:-1], start=1):
        if row[5] or row[6]:
            resumo_style.append(('BACKGROUND', (0, idx), (-1, idx), yellow_row))
    resumo_table.setStyle(TableStyle(resumo_style))
    story.extend([resumo_table, Spacer(1, 0.45 * cm)])

    glosas_sem_justificativa = [x for x in ocorrencias if x.get('status') == 'GLOSA']
    story.extend([section_bar(f"INCONFORMES SEM JUSTIFICATIVA ({len(glosas_sem_justificativa)} ocorrência(s))"), Spacer(1, 0.16 * cm)])
    if not glosas_sem_justificativa:
        story.extend([Paragraph("✓ Nenhum inconforme puro neste período.", normal), Spacer(1, 0.45 * cm)])
    else:
        glosas_rows = [['MATRÍC.', 'NOME', 'DATA', 'TIPO', 'MOTIVO']]
        for o in glosas_sem_justificativa:
            glosas_rows.append([o.get('matricula'), p(o.get('nome')), o.get('data'), o.get('tipo_refeicao'), p(descricao_relatorio(o))])
        glosas_table = make_table(glosas_rows, widths=[1.5*cm, 4.6*cm, 1.8*cm, 1.8*cm, 7.3*cm], header=True, font_size=6.2, body_fill=red_row)
        story.extend([glosas_table, Spacer(1, 0.45 * cm)])

    story.extend([section_bar("RELATÓRIOS INDIVIDUAIS POR COLABORADOR"), Spacer(1, 0.24 * cm)])
    for mat, item in sorted(por_colab.items(), key=lambda kv: str(kv[0])):
        glosa_valor = sum(
            (parse_money(o.get('valor_total_refeicao')) or Decimal('0'))
            for o in item['ocorrencias']
            if o.get('status') == 'GLOSA'
        )
        if not glosa_valor and item['glosa'] and not financeiro.get('valor_unitario_variavel'):
            glosa_valor = Decimal(item['glosa']) * (parse_money(financeiro.get('valor_unitario')) or Decimal('0'))
        colab_info = [[
            p(f"Matrícula: {mat}", meta),
            p(f"Nome: {item['nome']}", meta),
            p(f"Total: {item['total']}", meta),
            p(f"Conformes: {item['ok'] + item['excecao']}", meta),
            p(f"Inconformes: {item['glosa']}", meta),
            p(f"Glosa: {dinheiro(glosa_valor)}", meta),
        ]]
        info_table = Table(colab_info, colWidths=[2.0*cm, 4.3*cm, 1.45*cm, 2.1*cm, 2.2*cm, 2.4*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_blue),
            ('GRID', (0, 0), (-1, -1), 0.25, grid),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(info_table)
        rows = [['DATA', 'DIA', 'TIPO', 'ENTRADA', 'SAÍDA', 'RESULTADO', 'MOTIVO']]
        for o in sorted(item['ocorrencias'], key=lambda x: dataParaOrdenacao_py(x.get('data'))):
            rows.append([
                texto_celula(o.get('data')),
                texto_celula(o.get('dia_semana')),
                texto_celula(o.get('tipo_refeicao')),
                texto_celula(o.get('entrada')),
                texto_celula(o.get('saida')),
                resultado_pdf(o.get('status')),
                p(descricao_relatorio(o)),
            ])
        detalhe = make_table(rows, widths=[1.75*cm, 1.0*cm, 1.65*cm, 1.4*cm, 1.4*cm, 3.0*cm, 4.4*cm], header=True, font_size=6.1, header_fill_color=blue)
        detalhe = add_status_row_colors(detalhe, rows, 5)
        detalhe.setStyle(TableStyle([('ALIGN', (0, 0), (5, -1), 'CENTER')]))
        story.append(detalhe)
        story.append(Spacer(1, 0.22 * cm))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return output
