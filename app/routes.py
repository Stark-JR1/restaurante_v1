from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Blueprint, Response, jsonify, request, send_file

from app.parsers.excel_parser import parse_excel_refeicoes
from app.parsers.pdf_parser import parse_pdf_pontos
from app.services.auditoria_service import auditar, calcular_financeiro
from app.services.relatorio_service import gerar_pdf_auditoria
from app.utils.helpers import format_date, limpar_mojibake, limpar_textos

bp = Blueprint("auditoria", __name__)


@bp.route('/')
def index():
    html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
    return Response(html, content_type='text/html; charset=utf-8')


@bp.route('/api/analisar', methods=['POST'])
def analisar():
    try:
        if 'pdf_ponto' not in request.files:
            return jsonify({'erro': 'Cartão de ponto (PDF) não enviado.'}), 400
        if 'excel_refeicoes' not in request.files:
            return jsonify({'erro': 'Planilha de refeições (Excel) não enviada.'}), 400

        pdf_files = request.files.getlist('pdf_ponto')
        excel_file = request.files['excel_refeicoes']

        refeicoes_data = limpar_textos(parse_excel_refeicoes(excel_file.read()))
        pontos_por_matricula = {}
        erros_pdf = []

        for pdf_file in pdf_files:
            if not pdf_file or not pdf_file.filename:
                continue
            try:
                pontos_pdf = limpar_textos(parse_pdf_pontos(pdf_file.read()))
                pontos_por_matricula.update(pontos_pdf)
            except Exception as exc:
                erros_pdf.append(limpar_mojibake(f"{pdf_file.filename}: {exc}"))

        if not pontos_por_matricula and erros_pdf:
            return jsonify({'erro': 'Nenhum cartão de ponto válido foi processado.', 'detalhes': erros_pdf}), 400

        ocorrencias = auditar(refeicoes_data, pontos_por_matricula)
        financeiro = calcular_financeiro(refeicoes_data, ocorrencias)

        total = len(ocorrencias)
        # OK/GLOSA representam refeições e devem respeitar QUANTIDADE.
        ok = sum(int(o.get('quantidade', 1) or 1) for o in ocorrencias if o['status'] == 'OK' and o.get('origem') == 'REFEIÇÕES')
        glosas = sum(int(o.get('quantidade', 1) or 1) for o in ocorrencias if o['status'] == 'GLOSA' and o.get('origem') == 'REFEIÇÕES')
        excecoes = sum(int(o.get('quantidade', 1) or 1) for o in ocorrencias if o['status'] == 'EXCEÇÃO' and o.get('origem') == 'REFEIÇÕES')
        alertas = sum(1 for o in ocorrencias if o['status'] == 'ALERTA')
        pendentes = sum(1 for o in ocorrencias if o['status'] == 'PENDENTE')
        divergencias = sum(1 for o in ocorrencias if o['status'] == 'DIVERGÊNCIA')
        sem_cartao = sum(1 for o in ocorrencias if 'não possui cartão de ponto' in o.get('motivo', ''))

        periodos_inicio = [p['periodo_inicio'] for p in pontos_por_matricula.values() if p.get('periodo_inicio')]
        periodos_fim = [p['periodo_fim'] for p in pontos_por_matricula.values() if p.get('periodo_fim')]
        periodo_cartoes_inicio = min(periodos_inicio) if periodos_inicio else None
        periodo_cartoes_fim = max(periodos_fim) if periodos_fim else None

        funcionario = {'matricula': None, 'nome': 'Todos os colaboradores', 'periodo_inicio': '', 'periodo_fim': ''}
        if len(pontos_por_matricula) == 1:
            ponto_unico = next(iter(pontos_por_matricula.values()))
            funcionario = {
                'matricula': ponto_unico['matricula'],
                'nome': refeicoes_data['colaboradores'].get(ponto_unico['matricula'], ponto_unico.get('nome')),
                'periodo_inicio': format_date(ponto_unico['periodo_inicio']),
                'periodo_fim': format_date(ponto_unico['periodo_fim']),
            }

        payload = {
            'sucesso': True,
            'periodo_excel': {
                'inicio': format_date(refeicoes_data['periodo_inicio']),
                'fim': format_date(refeicoes_data['periodo_fim'])
            },
            'periodo_cartoes': {
                'inicio': format_date(periodo_cartoes_inicio),
                'fim': format_date(periodo_cartoes_fim)
            },
            'restaurante': refeicoes_data.get('restaurante', {}).get('nome') or 'RESTAURANTE',
            'restaurante_dados': refeicoes_data.get('restaurante', {}),
            'funcionario': funcionario,
            'resumo': {
                'total': total,
                'total_refeicoes': sum(ref.get('quantidade', 1) for ref in refeicoes_data['refeicoes']),
                'ok': ok,
                'glosas': glosas,
                'excecoes': excecoes,
                'alertas': alertas,
                'pendentes': pendentes,
                'divergencias': divergencias,
                'sem_cartao': sem_cartao,
            },
            'financeiro': financeiro,
            'ocorrencias': ocorrencias,
            'erros_pdf': erros_pdf
        }
        return jsonify(limpar_textos(payload))
    except Exception as e:
        import traceback
        return jsonify({'erro': str(e), 'trace': traceback.format_exc()}), 500


@bp.route('/api/exportar', methods=['POST'])
def exportar():
    try:
        data = limpar_textos(request.get_json())
        ocorrencias = data.get('ocorrencias', [])
        funcionario = data.get('funcionario', {})

        df = pd.DataFrame(ocorrencias)
        if df.empty:
            return jsonify({'erro': 'Nenhuma ocorrência para exportar.'}), 400

        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.rename(columns={
                'matricula': 'Matrícula',
                'nome': 'Nome',
                'data': 'Data',
                'dia_semana': 'Dia',
                'tipo_refeicao': 'Tipo Refeição',
                'status': 'Status',
                'descricao': 'Descrição',
                'motivo': 'Motivo',
                'entrada': 'Entrada',
                'saida_almoco': 'Saída Almoço',
                'retorno_almoco': 'Retorno Almoço',
                'saida': 'Saída',
                'total_trabalhado': 'Total Trabalhado',
                'autorizacao_status': 'Autorização Status',
                'autorizacao_motivo': 'Autorização Motivo',
                'acao_recomendada': 'Ação Recomendada',
                'aprovado_manual': 'Aprovado Manualmente',
                'origem': 'Origem',
                'linha_excel': 'Linha Excel',
                'numero_controle': 'Nº Controle',
                'quantidade': 'Quantidade',
                'valor_unitario': 'Valor Unitário',
                'valor_total_refeicao': 'Valor Lançamento'
            }).to_excel(writer, index=False, sheet_name='Auditoria')

            ws = writer.sheets['Auditoria']
            for col in ws.columns:
                max_len = max(len(str(c.value or '')) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

        output.seek(0)
        nome = funcionario.get('nome', 'colaborador').replace(' ', '_')
        filename = f"Auditoria_{nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/exportar_pdf', methods=['POST'])
def exportar_pdf():
    try:
        data = limpar_textos(request.get_json())
        ocorrencias = data.get('ocorrencias', [])
        if not ocorrencias:
            return jsonify({'erro': 'Nenhuma ocorrência para exportar.'}), 400

        output = gerar_pdf_auditoria(data)
        filename = f"Auditoria_Refeicoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except ModuleNotFoundError as e:
        if e.name == "reportlab":
            return jsonify({'erro': 'Biblioteca reportlab não instalada. Execute: pip install -r requirements.txt'}), 500
        return jsonify({'erro': str(e)}), 500
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
