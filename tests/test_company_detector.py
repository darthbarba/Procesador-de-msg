import pytest

from services.company_detector import detect_company


@pytest.mark.parametrize(
    ("sender", "expected_name", "expected_domain"),
    [
        ("Microsoft <billing@microsoft.com>", "Microsoft", "microsoft.com"),
        ("Billing <billing@MICROSOFT.COM>", "Microsoft", "microsoft.com"),
    ],
)
def test_detect_company_from_external_sender(sender, expected_name, expected_domain):
    result = detect_company(sender=sender, subject=None, body=None)

    assert result == {
        "name": expected_name,
        "domain": expected_domain,
        "source": "sender",
        "confidence": "high",
    }


def test_detect_company_prioritizes_forwarded_sender_over_internal_sender():
    result = detect_company(
        sender='"Zanin, Miguel - Sistemas" <mzanin@iapserseguros.seg.ar>',
        subject="FW: aviso",
        body="De: Microsoft <microsoft-noreply@microsoft.com>",
    )

    assert result == {
        "name": "Microsoft",
        "domain": "microsoft.com",
        "source": "forwarded_sender",
        "confidence": "high",
    }


def test_detect_company_supports_from_header_in_forwarded_body():
    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject=None,
        body="From: billing@empresaabc.com.ar",
    )

    assert result == {
        "name": "Empresaabc",
        "domain": "empresaabc.com.ar",
        "source": "forwarded_sender",
        "confidence": "high",
    }


def test_detect_company_returns_unknown_for_internal_sender_without_external_forward():
    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject=None,
        body="Mensaje interno sin remitente externo",
    )

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


@pytest.mark.parametrize(
    "sender",
    [
        "Persona <persona@gmail.com>",
        "Persona <persona@hotmail.com>",
        "Persona <persona@outlook.com>",
    ],
)
def test_detect_company_ignores_generic_sender_domains(sender):
    result = detect_company(sender=sender, subject=None, body=None)

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def test_detect_company_picks_first_valid_external_forwarded_sender():
    body = "\n".join(
        [
            "De: Interno <usuario@iapserseguros.seg.ar>",
            "From: externo@proveedor.com",
            "From: otro@contoso.com",
        ]
    )

    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject=None,
        body=body,
    )

    assert result == {
        "name": "Proveedor",
        "domain": "proveedor.com",
        "source": "forwarded_sender",
        "confidence": "high",
    }


def test_detect_company_prioritizes_forwarded_sender_over_external_sender():
    result = detect_company(
        sender="Facturacion <billing@contoso.com>",
        subject="Reenvio",
        body="From: microsoft-noreply@microsoft.com",
    )

    assert result == {
        "name": "Microsoft",
        "domain": "microsoft.com",
        "source": "forwarded_sender",
        "confidence": "high",
    }


def test_detect_company_handles_body_none():
    result = detect_company(
        sender="Proveedor <notificaciones@proveedor.com>",
        subject=None,
        body=None,
    )

    assert result == {
        "name": "Proveedor",
        "domain": "proveedor.com",
        "source": "sender",
        "confidence": "high",
    }


def test_detect_company_handles_empty_body():
    result = detect_company(
        sender="Proveedor <notificaciones@proveedor.com>",
        subject=None,
        body="",
    )

    assert result == {
        "name": "Proveedor",
        "domain": "proveedor.com",
        "source": "sender",
        "confidence": "high",
    }


def test_detect_company_handles_sender_none():
    result = detect_company(sender=None, subject=None, body=None)

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def test_detect_company_supports_com_ar_domains():
    result = detect_company(
        sender="Avisos <facturacion@empresaabc.com.ar>",
        subject=None,
        body=None,
    )

    assert result == {
        "name": "Empresaabc",
        "domain": "empresaabc.com.ar",
        "source": "sender",
        "confidence": "high",
    }


def test_detect_company_builds_readable_name_from_hyphenated_domain():
    result = detect_company(
        sender="Avisos <facturacion@proveedor-x.com>",
        subject=None,
        body=None,
    )

    assert result == {
        "name": "Proveedor X",
        "domain": "proveedor-x.com",
        "source": "sender",
        "confidence": "high",
    }


def test_detect_company_never_uses_iapser_domain_as_company():
    result = detect_company(
        sender="Interno <usuario@iapserseguros.seg.ar>",
        subject=None,
        body="From: usuario@iapserseguros.seg.ar",
    )

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def test_detect_company_never_uses_institutoseguro_domain_as_company():
    result = detect_company(
        sender="Interno <usuario@institutoseguro.com.ar>",
        subject=None,
        body="From: usuario@institutoseguro.com.ar",
    )

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def test_detect_company_result_name_is_safe_for_sharepoint():
    result = detect_company(
        sender='Facturación: LATAM? <billing@proveedor-x.com>',
        subject=None,
        body=None,
    )

    assert result["name"] == "Proveedor X"
    assert not any(char in result["name"] for char in '"#%*:<>?/\\|')


def test_detect_company_ignores_subject_as_signal():
    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject="Factura Microsoft urgente",
        body="Mensaje sin remitente externo",
    )

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }


def test_detect_company_skips_generic_forwarded_sender_and_uses_external_one():
    body = "\n".join(
        [
            "From: persona@gmail.com",
            "From: billing@proveedor.com",
        ]
    )

    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject=None,
        body=body,
    )

    assert result == {
        "name": "Proveedor",
        "domain": "proveedor.com",
        "source": "forwarded_sender",
        "confidence": "high",
    }


def test_detect_company_ignores_non_email_forwarded_lines():
    body = "\n".join(
        [
            "De: Microsoft",
            "From: no-es-un-email",
        ]
    )

    result = detect_company(
        sender='"Interno" <usuario@iapserseguros.seg.ar>',
        subject=None,
        body=body,
    )

    assert result == {
        "name": "Sin identificar",
        "domain": None,
        "source": "unknown",
        "confidence": "unknown",
    }
