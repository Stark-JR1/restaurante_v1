import io
import re
from datetime import date, datetime, time

import pdfplumber


def _minutos_horario(valor: time) -> int:
    return valor.hour * 60 + valor.minute


def _minutos_trabalhados(batidas: list[time]) -> int | None:
    if len(batidas) < 2 or len(batidas) % 2:
        return None
    total = 0
    for entrada, saida in zip(batidas[::2], batidas[1::2]):
        inicio = _minutos_horario(entrada)
        fim = _minutos_horario(saida)
        if fim < inicio:
            fim += 24 * 60
        total += fim - inicio
    return total


def separar_batidas_total(horarios: list[time]) -> tuple[list[time], time | None, list[time]]:
    """Separa marcacoes reais do total trabalhado e das horas extras."""
    for quantidade_batidas in (4, 2):
        if len(horarios) <= quantidade_batidas:
            continue
        total_calculado = _minutos_trabalhados(horarios[:quantidade_batidas])
        total_informado = _minutos_horario(horarios[quantidade_batidas])
        if total_calculado is not None and abs(total_calculado - total_informado) <= 5:
            return horarios[:quantidade_batidas], horarios[quantidade_batidas], horarios[quantidade_batidas + 1:]
    return horarios, None, []


def parse_texto_cartao_ponto(full_text: str) -> dict:
    if not full_text.strip():
        raise ValueError("Cartão de ponto sem texto extraível.")

    result = {
        'matricula': None,
        'nome': None,
        'periodo_inicio': None,
        'periodo_fim': None,
        'dias': {}
    }

    lines = full_text.splitlines()

    for line in lines:
        m = re.search(r'Empregado:\s*(\d+)\s+(.+?)(?:\s+Escala\s*:|\s+Turma\s*:|$)', line)
        if m:
            result['matricula'] = int(m.group(1))
            result['nome'] = m.group(2).strip()
            break

    for line in lines:
        m = re.search(r'(\d{2}/\d{2}/\d{4})\s*a\s+(\d{2}/\d{2}/\d{4})', line, re.IGNORECASE)
        if m:
            result['periodo_inicio'] = datetime.strptime(m.group(1), '%d/%m/%Y').date()
            result['periodo_fim'] = datetime.strptime(m.group(2), '%d/%m/%Y').date()
            break

    if not result['periodo_inicio']:
        raise ValueError("Não foi possível identificar o período no cartão de ponto.")

    ano = result['periodo_inicio'].year
    mes = result['periodo_inicio'].month

    status_especial = {
        '9997': 'feriado',
        '9998': 'compensado',
        '9999': 'dsr',
    }
    dia_re = re.compile(r'^(\d{2})\s+(SEG|TER|QUA|QUI|SEX|SAB|DOM)\s+(\d{4})\s+(.*)')

    for line in lines:
        m = dia_re.match(line.strip())
        if not m:
            continue

        dia_num = int(m.group(1))
        cod_escala = m.group(3)
        resto = m.group(4).strip()

        try:
            d = date(ano, mes, dia_num)
        except ValueError:
            continue

        horarios = re.findall(r'\b(\d{2}:\d{2})\b', resto)
        horarios_time = []
        for h in horarios:
            try:
                horarios_time.append(datetime.strptime(h, '%H:%M').time())
            except ValueError:
                pass

        batidas, total_trabalhado, horas_extras = separar_batidas_total(horarios_time)

        entrada = batidas[0] if batidas else None
        saida_almoco = batidas[1] if len(batidas) >= 2 else None
        retorno_almoco = batidas[2] if len(batidas) >= 3 else None
        saida = batidas[-1] if len(batidas) >= 2 else None
        status = status_especial.get(cod_escala, 'trabalhando')
        if batidas and status in {'dsr', 'compensado', 'feriado'}:
            status = 'trabalhando'

        result['dias'][d] = {
            'status': status,
            'dia_semana': m.group(2),
            'codigo_escala': cod_escala,
            'entrada': entrada,
            'saida_almoco': saida_almoco,
            'retorno_almoco': retorno_almoco,
            'saida': saida,
            'marcacoes': batidas,
            'total_trabalhado': total_trabalhado,
            'horas_extras': horas_extras
        }

    return result


def parse_pdf_ponto(pdf_bytes: bytes) -> dict:
    pontos = parse_pdf_pontos(pdf_bytes)
    if not pontos:
        raise ValueError("Nenhum cartão de ponto válido encontrado no PDF.")
    return next(iter(pontos.values()))


def parse_pdf_pontos(pdf_bytes: bytes) -> dict:
    pontos = {}
    erros = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                erros.append(f"Página {page_num}: sem texto extraível.")
                continue

            blocos = re.split(r'(?=CARTÃO DE PONTO\s+Período:)', text)
            blocos = [b.strip() for b in blocos if b.strip()]
            if not blocos:
                blocos = [text]

            for bloco in blocos:
                if "Empregado:" not in bloco:
                    continue
                try:
                    ponto = parse_texto_cartao_ponto(bloco)
                    matricula = ponto.get('matricula')
                    if matricula is None:
                        erros.append(f"Página {page_num}: matrícula não identificada.")
                        continue
                    pontos[matricula] = ponto
                except Exception as exc:
                    erros.append(f"Página {page_num}: {exc}")

    if not pontos:
        detalhe = " ".join(erros[:3])
        raise ValueError(f"PDF ilegível ou sem cartões de ponto válidos. {detalhe}".strip())

    return pontos
