import unicodedata
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import re


MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€“", "â€”", "â€¦", "â€¢", "â„¢", "ðŸ", "ƒ", "Š", "‡", "œ", "�")
MOJIBAKE_RUN_RE = re.compile(
    r"[\u0080-\u00ff\u0152\u0153\u0160\u0161\u0178\u0192"
    r"\u02c6\u02dc\u2013\u2014\u2018\u2019\u201a\u201c\u201d"
    r"\u201e\u2020\u2021\u2022\u2026\u2030\u2039\u203a\u20ac]+"
)


def _mojibake_score(texto: str) -> int:
    return sum(texto.count(marker) for marker in MOJIBAKE_MARKERS) + texto.count("\ufffd") * 3


def _corrigir_bloco_mojibake(texto: str) -> str:
    melhor = texto
    melhor_score = _mojibake_score(texto)
    fila = [texto]
    vistos = {texto}

    for _ in range(4):
        proximos = []
        for item in fila:
            for encoding in ("cp1252", "latin1"):
                try:
                    candidato = item.encode(encoding).decode("utf-8")
                except UnicodeError:
                    continue
                if candidato in vistos:
                    continue
                vistos.add(candidato)
                score = _mojibake_score(candidato)
                if score < melhor_score:
                    melhor = candidato
                    melhor_score = score
                proximos.append(candidato)
        fila = proximos
        if not fila:
            break

    return melhor


def limpar_mojibake(valor):
    if valor is None or not isinstance(valor, str):
        return valor
    if not any(marker in valor for marker in MOJIBAKE_MARKERS):
        return valor
    return MOJIBAKE_RUN_RE.sub(lambda match: _corrigir_bloco_mojibake(match.group(0)), valor)


def limpar_textos(valor):
    if isinstance(valor, str):
        return limpar_mojibake(valor)
    if isinstance(valor, list):
        return [limpar_textos(item) for item in valor]
    if isinstance(valor, tuple):
        return tuple(limpar_textos(item) for item in valor)
    if isinstance(valor, dict):
        return {key: limpar_textos(item) for key, item in valor.items()}
    return valor


def normalizar_texto(valor) -> str:
    texto = "" if valor is None else str(limpar_mojibake(str(valor)))
    texto = " ".join(texto.strip().split()).upper()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def parse_date_value(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, fmt).date()
            except ValueError:
                pass
    return None


def parse_money(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor))
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def first_value_after(row, start_idx, predicate):
    for value in row[start_idx + 1:]:
        if predicate(value):
            return value
    return None


def first_money_after(row, start_idx):
    return first_value_after(row, start_idx, lambda value: parse_money(value) is not None)


def first_text_after(row, start_idx):
    return first_value_after(row, start_idx, lambda value: bool(normalizar_texto(value)))


def quantidade_marcacao_refeicao(valor) -> int:
    if valor is None:
        return 0
    if isinstance(valor, (int, float)):
        return int(valor) if valor > 0 else 0

    texto = normalizar_texto(valor)
    if texto in {"X", "SIM", "S", "OK"}:
        return 1
    try:
        numero = Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return 0
    return int(numero) if numero > 0 else 0


def is_marcacao_refeicao(valor) -> bool:
    return quantidade_marcacao_refeicao(valor) > 0


def format_date(d):
    return d.strftime("%d/%m/%Y") if isinstance(d, date) else ""


def format_time(t):
    return t.strftime("%H:%M") if isinstance(t, time) else ""


def ajustar_horario(t: time, minutos: int) -> time:
    base = datetime.combine(date(2000, 1, 1), t)
    return (base + timedelta(minutes=minutos)).time()


def tipo_refeicao_norm(valor) -> str:
    texto = normalizar_texto(valor)
    if texto in {"TODAS", "TODOS", "GERAL", "REFEICAO", "REFEIÇÃO", "LIBERADO"} or "REFEI" in texto:
        return "GERAL"
    if "ALMOC" in texto or "ALMO" in texto:
        return "ALMOÇO"
    if "JANTA" in texto or "JANTAR" in texto:
        return "JANTA"
    if "CAFE" in texto:
        return "CAFÉ"
    return texto


def normalizar_tipo_refeicao(valor) -> list[str]:
    texto = normalizar_texto(valor)
    if not texto:
        return []

    texto = texto.replace("\\", "/")
    import re
    partes = re.split(r"/|,|;|\+|\s+E\s+", texto)
    tipos = []

    for parte in partes:
        p = normalizar_texto(parte)
        if "ALMOC" in p or "ALMO" in p:
            tipos.append("ALMOCO")
        elif "JANTA" in p or "JANTAR" in p:
            tipos.append("JANTA")
        elif "CAFE" in p or p.startswith("CAF"):
            tipos.append("CAFE")

    return sorted(set(tipos))


def normalizar_autorizado(valor) -> bool | None:
    texto = normalizar_texto(valor)
    if texto in {"S", "SIM", "YES", "Y"}:
        return True
    if texto in {"N", "NAO", "NÃO", "NO"} or (texto.startswith("N") and texto.endswith("O") and len(texto) <= 4):
        return False
    return None
