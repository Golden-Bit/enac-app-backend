from pydantic import BaseModel, Field


class Client(BaseModel):
    """Modello anagrafica cliente (valori di default generici)."""

    name: str = Field("Cliente Placeholder", description="Ragione sociale o nome completo")
    address: str | None = Field(None, description="Indirizzo completo (via, numero, CAP, città)")
    tax_code: str | None = Field(None, description="Codice fiscale")
    vat: str | None = Field(None, description="Partita IVA")
    phone: str | None = Field(None, description="Telefono principale")
    email: str | None = Field(None, description="Indirizzo e‑mail")
    sector: str | None = Field(None, description="Codice ATECO o settore di attività")
    legal_rep: str | None = Field(None, description="Legale rappresentante")
    legal_rep_tax_code: str | None = Field(None, description="Codice fiscale del legale rappresentante")

    class Config:
        schema_extra = {
            "example": {
                "name": "Cliente Placeholder",
                "address": "Via Generica 123, 00100 Città",
                "tax_code": "ABCDEF12G34H567I",
                "vat": "01234567890",
                "phone": "+39 06 1234567",
                "email": "cliente@example.com",
                "sector": "62.01",
                "legal_rep": "Mario Rossi",
                "legal_rep_tax_code": "RSSMRA80A01H501U",
            }
        }