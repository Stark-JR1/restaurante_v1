def contar_colaboradores_com_ocorrencia(ocorrencias: list[dict]) -> int:
    return len({o.get('matricula') for o in ocorrencias if o.get('matricula')})
