"""Unrelated existing billing behavior; checkout scenarios must leave it unchanged."""


def invoice_label(number):
    return f"invoice-{number:06d}"
