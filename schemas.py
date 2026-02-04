from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

# ---- output used by /voitures/by-matricule ----
class VoitureOut(BaseModel):
    id: int
    id_proprietaire: int
    id_type_voiture: int
    matricule: str
    remarques: Optional[str] = None
    cree_le: datetime

    class Config:
        from_attributes = True

class ReparationOut(BaseModel):
    id: int
    id_voiture: int
    date_visite: datetime
    probleme_signale: str
    diagnostic: Optional[str] = None
    reparation_effectuee: str
    prix: Optional[float] = None
    statut: str
    cree_le: datetime

    class Config:
        from_attributes = True

class VoitureAvecHistoriqueOut(BaseModel):
    voiture: VoitureOut
    historique: List[ReparationOut]


# ---- SIMPLE payloads ----
class EnregistrementSimpleCreate(BaseModel):
    numero_serie: str
    marque: str
    nom_proprietaire: str
    telephone: str
    date_visite: Optional[datetime] = None
    reparation: str

class EnregistrementSimpleOut(BaseModel):
    id_voiture: int
    id_reparation: int   # ✅ add this
    numero_serie: str
    marque: str
    nom_proprietaire: str
    telephone: str
    date_visite: datetime
    reparation: str


# ---- UPDATE payloads ----
class VoitureUpdate(BaseModel):
    marque: Optional[str] = None
    nom_proprietaire: Optional[str] = None
    telephone: Optional[str] = None

class ReparationUpdate(BaseModel):
    date_visite: Optional[datetime] = None
    probleme_signale: Optional[str] = None
    reparation_effectuee: Optional[str] = None
    diagnostic: Optional[str] = None
    prix: Optional[float] = None
    statut: Optional[str] = None  # EN_COURS | TERMINEE | ANNULEE
