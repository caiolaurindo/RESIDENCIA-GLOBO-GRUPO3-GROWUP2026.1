"""
tests/test_validacao.py
─────────────────────────────────────────────────────────────────────
Testes unitários para a camada de validação de vocabulário.

Execute com:
    python -m pytest tests/ -v
─────────────────────────────────────────────────────────────────────
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Garante que o pacote raiz seja encontrado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────
# Mock do banco VLibras (evita dependência dos arquivos JSON nos testes)
# ─────────────────────────────────────────────────────────────────────

VOCAB_MOCK = {
    "CASA": "CASA",
    "OLA": "OLA",
    "ABANDONAR": "1S_ABANDONAR_1S",
    "QUILOMETRO": "0_QUILÔMETRO",
    "BOM": "BOM",
}

LEMA_MOCK = {
    "ABANDONAR": "1S_ABANDONAR_1S",
    "QUILOMETRO": "0_QUILÔMETRO",
}


def mock_buscar_termo(palavra: str):
    from app.services.vlibras_db import normalizar
    chave = normalizar(palavra)
    if chave in VOCAB_MOCK:
        return VOCAB_MOCK[chave]
    if chave in LEMA_MOCK:
        return LEMA_MOCK[chave]
    return None


# ─────────────────────────────────────────────────────────────────────
# TESTES: vlibras_db
# ─────────────────────────────────────────────────────────────────────

class TestNormalizacao(unittest.TestCase):

    def test_remove_acentos(self):
        from app.services.vlibras_db import normalizar
        self.assertEqual(normalizar("abandonár"), "ABANDONAR")
        self.assertEqual(normalizar("quilômetro"), "QUILOMETRO")
        self.assertEqual(normalizar("olá"), "OLA")

    def test_maiusculas(self):
        from app.services.vlibras_db import normalizar
        self.assertEqual(normalizar("casa"), "CASA")

    def test_extrai_lema_simples(self):
        from app.services.vlibras_db import _extrair_lema
        self.assertEqual(_extrair_lema("1S_ABANDONAR_1S"), "ABANDONAR")
        self.assertEqual(_extrair_lema("0_QUILÔMETRO"), "QUILÔMETRO")

    def test_extrai_lema_sem_prefixo(self):
        from app.services.vlibras_db import _extrair_lema
        # Sem prefixo numérico → retorna None (não é lema diferente)
        self.assertIsNone(_extrair_lema("CASA"))


# ─────────────────────────────────────────────────────────────────────
# TESTES: tokenização
# ─────────────────────────────────────────────────────────────────────

class TestTokenizacao(unittest.TestCase):

    def test_remove_pontuacao(self):
        from app.services.validacao_service import tokenizar
        tokens = tokenizar("Olá, como você está?")
        self.assertNotIn(",", " ".join(tokens))
        self.assertNotIn("?", " ".join(tokens))

    def test_remove_ruidos(self):
        from app.services.validacao_service import tokenizar
        tokens = tokenizar("Hmm, ah, eu quero ir.")
        palavras = [t.lower() for t in tokens]
        self.assertNotIn("hmm", palavras)
        self.assertNotIn("ah", palavras)

    def test_tokens_validos(self):
        from app.services.validacao_service import tokenizar
        tokens = tokenizar("eu tenho uma casa bonita")
        self.assertEqual(len(tokens), 5)


# ─────────────────────────────────────────────────────────────────────
# TESTES: validar_token
# ─────────────────────────────────────────────────────────────────────

class TestValidarToken(unittest.TestCase):

    @patch("app.services.validacao_service.buscar_termo", side_effect=mock_buscar_termo)
    def test_encontra_exato(self, _):
        from app.services.validacao_service import validar_token
        r = validar_token("casa")
        self.assertEqual(r["termo_vlibras"], "CASA")
        self.assertTrue(r["validado"])

    @patch("app.services.validacao_service.buscar_termo", side_effect=mock_buscar_termo)
    def test_encontra_por_lema(self, _):
        from app.services.validacao_service import validar_token
        r = validar_token("abandonar")
        self.assertEqual(r["termo_vlibras"], "1S_ABANDONAR_1S")
        self.assertTrue(r["validado"])

    @patch("app.services.validacao_service.buscar_termo", return_value=None)
    @patch("app.services.validacao_service.resolver_via_sinonimo")
    def test_fallback_sinonimo(self, mock_resolver, _):
        mock_resolver.return_value = {
            "palavra_original": "residencia",
            "sinonimos_testados": ["casa"],
            "termo_vlibras": "CASA",
            "estrategia": "sinonimo",
        }
        from app.services.validacao_service import validar_token
        r = validar_token("residencia")
        self.assertEqual(r["termo_vlibras"], "CASA")
        self.assertEqual(r["estrategia"], "sinonimo")

    @patch("app.services.validacao_service.buscar_termo", return_value=None)
    @patch("app.services.validacao_service.resolver_via_sinonimo")
    def test_fallback_datilologia(self, mock_resolver, _):
        mock_resolver.return_value = {
            "palavra_original": "xpto",
            "sinonimos_testados": ["a", "b", "c"],
            "termo_vlibras": "X P T O",
            "estrategia": "datilologia",
        }
        from app.services.validacao_service import validar_token
        r = validar_token("xpto")
        self.assertEqual(r["estrategia"], "datilologia")
        self.assertFalse(r["validado"])


# ─────────────────────────────────────────────────────────────────────
# TESTES: datilologia
# ─────────────────────────────────────────────────────────────────────

class TestDatilologia(unittest.TestCase):

    def test_converte_letras(self):
        from app.services.sinonimo_service import _para_datilologia
        self.assertEqual(_para_datilologia("casa"), "C A S A")

    def test_ignora_numeros(self):
        from app.services.sinonimo_service import _para_datilologia
        resultado = _para_datilologia("123abc")
        self.assertEqual(resultado, "A B C")

    def test_vazio(self):
        from app.services.sinonimo_service import _para_datilologia
        self.assertIsNone(_para_datilologia("123"))


if __name__ == "__main__":
    unittest.main()