from __future__ import annotations
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

class DocumentoMeta(BaseModel):
    scope: Literal["CONTRATTO","TITOLO","SINISTRO","GARA"] = Field(..., description="Ambito")     # obblig.
    categoria: Literal["CND","APP","CLAIM","ALTRO"] = Field(..., description="Categoria")         # obblig.
    mime: str = Field(..., description="MIME")                                                    # obblig.
    nome_originale: str = Field(..., description="Nome file")                                     # obblig.
    size: int = Field(..., description="Dimensione")                                              # obblig.
    hash: Optional[str] = Field(None, description="SHA1")
    path_relativo: Optional[str] = Field(None, description="Percorso relativo blob")
    metadati: Dict[str, Any] = Field(default_factory=dict)

class CreateDocumentRequest(BaseModel):
    meta: DocumentoMeta = Field(..., description="Metadati documento")
    content_base64: Optional[str] = Field(None, description="Contenuto in base64 (opzionale)")

class CreateResponse(BaseModel):
    id: str = Field(...)

class DeleteResponse(BaseModel):
    deleted: bool = Field(True)
    id: str
