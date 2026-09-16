import unittest
from datetime import time

from app.parsers.pdf_parser import parse_texto_cartao_ponto, separar_batidas_total
from app.services.auditoria_service import jornada_permite_refeicao


class RegraAlmocoTest(unittest.TestCase):
    def test_separa_total_de_jornada_com_duas_batidas(self):
        batidas, total, extras = separar_batidas_total([time(8), time(12), time(4)])
        self.assertEqual(batidas, [time(8), time(12)])
        self.assertEqual(total, time(4))
        self.assertEqual(extras, [])

    def test_parser_aceita_jornada_08_as_12_para_almoco(self):
        texto = """CARTAO DE PONTO Periodo: 01/05/2026 a 31/05/2026
Empregado: 50193 JOAO PEDRO DIAS SOUZA
04 SEG 0412 08:00 12:00 04:00
"""
        ponto = parse_texto_cartao_ponto(texto)
        info = next(iter(ponto["dias"].values()))
        permitido, _motivo = jornada_permite_refeicao(info, "ALMOCO")
        self.assertTrue(permitido)
        self.assertEqual(info["saida"], time(12))
        self.assertEqual(info["total_trabalhado"], time(4))

    def test_limites_da_tolerancia_de_almoco(self):
        dentro = {"status": "trabalhando", "entrada": time(8), "saida": time(10, 30), "marcacoes": [time(8), time(10, 30)]}
        fora = {"status": "trabalhando", "entrada": time(8), "saida": time(9, 29), "marcacoes": [time(8), time(9, 29)]}
        self.assertTrue(jornada_permite_refeicao(dentro, "ALMOCO")[0])
        self.assertFalse(jornada_permite_refeicao(fora, "ALMOCO")[0])

    def test_regra_ignora_total_misturado_as_batidas(self):
        info = {
            "status": "trabalhando",
            "entrada": time(8),
            "saida": time(4),
            "marcacoes": [time(8), time(12), time(4)],
        }
        permitido, _motivo = jornada_permite_refeicao(info, "ALMOCO")
        self.assertTrue(permitido)

    def test_regras_sao_gerais_e_independentes_de_matricula(self):
        almoco_dentro = {"status": "trabalhando", "entrada": time(8), "saida": time(12), "marcacoes": [time(8), time(12)]}
        almoco_fora = {"status": "trabalhando", "entrada": time(6), "saida": time(9, 29), "marcacoes": [time(6), time(9, 29)]}
        cafe_dentro = {"status": "trabalhando", "entrada": time(7, 30), "saida": time(12), "marcacoes": [time(7, 30), time(12)]}
        cafe_fora = {"status": "trabalhando", "entrada": time(8, 31), "saida": time(12), "marcacoes": [time(8, 31), time(12)]}
        janta_dentro = {"status": "trabalhando", "entrada": time(13), "saida": time(18), "marcacoes": [time(13), time(18)]}
        janta_fora = {"status": "trabalhando", "entrada": time(8), "saida": time(17, 59), "marcacoes": [time(8), time(17, 59)]}

        self.assertTrue(jornada_permite_refeicao(almoco_dentro, "ALMOCO")[0])
        self.assertFalse(jornada_permite_refeicao(almoco_fora, "ALMOCO")[0])
        self.assertTrue(jornada_permite_refeicao(cafe_dentro, "CAFE")[0])
        self.assertFalse(jornada_permite_refeicao(cafe_fora, "CAFE")[0])
        self.assertTrue(jornada_permite_refeicao(janta_dentro, "JANTA")[0])
        self.assertFalse(jornada_permite_refeicao(janta_fora, "JANTA")[0])


if __name__ == "__main__":
    unittest.main()
