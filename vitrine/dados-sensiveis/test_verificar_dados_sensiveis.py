"""Testes da barreira de dados sensíveis.

Nenhum documento real aparece aqui, nem para servir de caso negativo. Os
documentos que precisam ter DV válido são CONSTRUÍDOS no próprio teste, a partir
de um prefixo arbitrário: assim o teste exercita a validação de verdade sem que
exista, em lugar nenhum do arquivo, uma sequência que alguém possa confundir com
documento de alguém.
"""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "verificador", Path(__file__).parent / "verificar_dados_sensiveis.py"
)
verificador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verificador)


def _cnpj_com_dv(base: str) -> str:
    """Completa 12 dígitos com os dois verificadores corretos."""
    assert len(base) == 12

    def digito(parcial: str) -> str:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(parcial):]
        resto = sum(int(d) * p for d, p in zip(parcial, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    primeiro = digito(base)
    return base + primeiro + digito(base + primeiro)


def _cpf_com_dv(base: str) -> str:
    assert len(base) == 9

    def digito(parcial: str, peso_inicial: int) -> str:
        soma = sum(int(d) * p for d, p in zip(parcial, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return "0" if resto == 10 else str(resto)

    primeiro = digito(base, 10)
    return base + primeiro + digito(base + primeiro, 11)


class TestDigitoVerificador:
    def test_cnpj_construido_passa_no_dv(self):
        assert verificador._dv_cnpj(_cnpj_com_dv("456789000123"))

    def test_cnpj_com_dv_errado_reprova(self):
        valido = _cnpj_com_dv("456789000123")
        errado = valido[:13] + str((int(valido[13]) + 1) % 10)
        assert not verificador._dv_cnpj(errado)

    def test_cnpj_de_digito_repetido_nao_e_documento(self):
        # 00000000000000 tem DV formalmente valido; tratar como documento faria
        # o verificador reprovar zero de preenchimento em toda parte.
        assert not verificador._dv_cnpj("7" * 14)

    def test_cpf_construido_passa_no_dv(self):
        assert verificador._dv_cpf(_cpf_com_dv("456789012"))

    def test_cpf_de_digito_repetido_nao_e_documento(self):
        assert not verificador._dv_cpf("3" * 11)


class TestDeteccaoNoTexto:
    def test_acha_cnpj_valido_fora_da_lista(self):
        documento = _cnpj_com_dv("456789000123")
        achados = verificador._achados_do_texto(f"empresa = '{documento}'")
        assert [(t, v) for _, t, v in achados] == [("CNPJ", documento)]

    def test_acha_mesmo_formatado_com_pontuacao(self):
        d = _cnpj_com_dv("456789000123")
        formatado = f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        achados = verificador._achados_do_texto(formatado)
        assert len(achados) == 1

    def test_ignora_documento_sintetico_declarado(self):
        for sintetico in verificador.DOCUMENTOS_SINTETICOS:
            assert verificador._achados_do_texto(sintetico) == []

    def test_ignora_numero_que_nao_e_documento(self):
        assert verificador._achados_do_texto("total = 12345678901234567890") == []

    def test_reporta_a_linha_certa(self):
        documento = _cnpj_com_dv("456789000123")
        texto = "\n".join(["primeira", "segunda", f"terceira {documento}"])
        assert verificador._achados_do_texto(texto)[0][0] == 3

    def test_chave_de_nfe_carrega_o_cnpj_do_emitente(self):
        emitente = _cnpj_com_dv("456789000123")
        chave = "43" + "2601" + emitente + "55" + "001" + "000000001" + "1" + "00000001" + "7"
        assert len(chave) == 44
        achados = verificador._achados_do_texto(chave)
        assert ("chave de NF-e", chave) in [(t, v) for _, t, v in achados]

    def test_chave_com_emitente_sintetico_passa(self):
        sintetico = "11222333000181"
        chave = "43" + "2601" + sintetico + "55" + "001" + "000000001" + "1" + "00000001" + "7"
        assert len(chave) == 44
        tipos = [t for _, t, _ in verificador._achados_do_texto(chave)]
        assert "chave de NF-e" not in tipos


class TestFiltroDeArquivo:
    @pytest.mark.parametrize("nome", ["logo.png", "certificado.pfx", "planilha.xlsx"])
    def test_binario_pela_extensao_nao_e_verificavel(self, nome):
        assert not verificador._verificavel(nome)

    @pytest.mark.parametrize("nome", ["app.py", ".env.example", "Dockerfile", "dados.sql"])
    def test_texto_sem_extensao_conhecida_e_verificavel(self, nome):
        assert verificador._verificavel(nome)

    def test_byte_nul_marca_binario(self):
        assert verificador._texto_ou_none(b"texto\0com nul") is None

    def test_sequencia_utf8_invalida_marca_binario(self):
        assert verificador._texto_ou_none(b"\xff\xfe\x00\x01") is None

    def test_utf8_acentuado_decodifica(self):
        assert verificador._texto_ou_none("emissão".encode()) == "emissão"
