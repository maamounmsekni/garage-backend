from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from database import engine, get_db
from models import Base, Proprietaire, TypeVoiture, Voiture, Reparation
from schemas import (
    VoitureAvecHistoriqueOut,
    EnregistrementSimpleCreate,
    EnregistrementSimpleOut,
    VoitureUpdate,
    ReparationUpdate,
)

app = FastAPI(title="Garage API")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utcnow():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------
# 1) history by matricule (sorted newest -> oldest)
# ------------------------------------------------------------
@app.get("/voitures/by-matricule/{matricule}", response_model=VoitureAvecHistoriqueOut)
def details_voiture_par_matricule(
    matricule: str = Path(..., min_length=1),
    db: Session = Depends(get_db),
):
    matricule = matricule.strip()

    v = (
        db.query(Voiture)
        .options(joinedload(Voiture.proprietaire))
        .filter(Voiture.matricule == matricule)
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Voiture introuvable")

    hist = (
        db.query(Reparation)
        .filter(Reparation.id_voiture == v.id)
        .order_by(Reparation.date_visite.desc(), Reparation.id.desc())  # ✅ tie-break
        .all()
    )
    return {"voiture": v, "historique": hist}


# ------------------------------------------------------------
# 2) create record (client can return again => new repair)
# ------------------------------------------------------------
@app.post("/enregistrements", response_model=EnregistrementSimpleOut)
def creer_enregistrement(payload: EnregistrementSimpleCreate, db: Session = Depends(get_db)):
    numero = (payload.numero_serie or "").strip()
    if not numero:
        raise HTTPException(status_code=422, detail="numero_serie obligatoire")

    # default type
    tv = db.query(TypeVoiture).filter(TypeVoiture.nom_type == "GENERIC").first()
    if not tv:
        tv = TypeVoiture(nom_type="GENERIC")
        db.add(tv)
        db.flush()

    # get car if exists
    v = (
        db.query(Voiture)
        .options(joinedload(Voiture.proprietaire))
        .filter(Voiture.matricule == numero)
        .first()
    )

    if not v:
        # create owner
        p = Proprietaire(
            nom_complet=(payload.nom_proprietaire or "").strip(),
            numero_telephone=(payload.telephone or "").strip(),
        )
        db.add(p)
        db.flush()

        # create car
        v = Voiture(
            id_proprietaire=p.id,
            id_type_voiture=tv.id,
            matricule=numero,
            remarques=(payload.marque or "").strip(),
        )
        db.add(v)
        db.flush()
        proprietaire = p
    else:
        # update owner/car if needed
        proprietaire = v.proprietaire
        if payload.nom_proprietaire:
            proprietaire.nom_complet = payload.nom_proprietaire.strip()
        if payload.telephone:
            proprietaire.numero_telephone = payload.telephone.strip()
        if payload.marque:
            v.remarques = payload.marque.strip()

    # always create a new repair row
    r = Reparation(
        id_voiture=v.id,
        date_visite=payload.date_visite or utcnow(),
        probleme_signale=(payload.reparation or "").strip(),
        reparation_effectuee=(payload.reparation or "").strip(),
        diagnostic=None,
        prix=None,
        statut="EN_COURS",
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    return {
        "id_voiture": v.id,
        "id_reparation": r.id,
        "numero_serie": v.matricule,
        "marque": v.remarques or "",
        "nom_proprietaire": proprietaire.nom_complet,
        "telephone": proprietaire.numero_telephone,
        "date_visite": r.date_visite,
        "reparation": r.reparation_effectuee,
    }


# ------------------------------------------------------------
# 3) list by numero_serie (sorted newest -> oldest)
# ------------------------------------------------------------
@app.get("/enregistrements/by-numero-serie/{numero_serie}", response_model=List[EnregistrementSimpleOut])
def lister_enregistrements_par_numero_serie(numero_serie: str, db: Session = Depends(get_db)):
    numero_serie = numero_serie.strip()

    v = (
        db.query(Voiture)
        .options(joinedload(Voiture.proprietaire))
        .filter(Voiture.matricule == numero_serie)
        .first()
    )
    if not v:
        return []

    reps = (
        db.query(Reparation)
        .filter(Reparation.id_voiture == v.id)
        .order_by(Reparation.date_visite.desc(), Reparation.id.desc())  # ✅ tie-break
        .all()
    )

    return [
        {
            "id_voiture": v.id,
            "id_reparation": r.id,
            "numero_serie": v.matricule,
            "marque": v.remarques or "",
            "nom_proprietaire": v.proprietaire.nom_complet,
            "telephone": v.proprietaire.numero_telephone,
            "date_visite": r.date_visite,
            "reparation": r.reparation_effectuee,
        }
        for r in reps
    ]


# ------------------------------------------------------------
# 4) list all enregistrements (sorted newest -> oldest)
# ------------------------------------------------------------
from sqlalchemy import or_

@app.get("/enregistrements", response_model=List[EnregistrementSimpleOut])
def lister_enregistrements(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None),         # partial text
    limit: int = Query(10, ge=1, le=1000),
):
    query = (
        db.query(Reparation, Voiture, Proprietaire)
        .join(Voiture, Reparation.id_voiture == Voiture.id)
        .join(Proprietaire, Voiture.id_proprietaire == Proprietaire.id)
        .order_by(Reparation.date_visite.desc(), Reparation.id.desc())  # ✅ newest first
    )

    if q:
        q = q.strip()
        like = f"%{q}%"

        query = query.filter(
            or_(
                Voiture.matricule.ilike(like),
                Voiture.remarques.ilike(like),                 # marque
                Proprietaire.nom_complet.ilike(like),
                Proprietaire.numero_telephone.ilike(like),
                Reparation.probleme_signale.ilike(like),
                Reparation.reparation_effectuee.ilike(like),
            )
        )

    rows = query.limit(limit).all()

    return [
        {
            "id_voiture": v.id,
            "id_reparation": r.id,
            "numero_serie": v.matricule,
            "marque": v.remarques or "",
            "nom_proprietaire": p.nom_complet,
            "telephone": p.numero_telephone,
            "date_visite": r.date_visite,
            "reparation": r.reparation_effectuee,
        }
        for (r, v, p) in rows
    ]



# ------------------------------------------------------------
# 5) update car + owner by numero_serie
# ------------------------------------------------------------
@app.put("/voitures/by-numero-serie/{numero_serie}")
def update_voiture(numero_serie: str, payload: VoitureUpdate, db: Session = Depends(get_db)):
    numero_serie = numero_serie.strip()

    v = (
        db.query(Voiture)
        .options(joinedload(Voiture.proprietaire))
        .filter(Voiture.matricule == numero_serie)
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Voiture introuvable")

    if payload.marque is not None:
        v.remarques = payload.marque.strip()

    if payload.nom_proprietaire is not None:
        v.proprietaire.nom_complet = payload.nom_proprietaire.strip()

    if payload.telephone is not None:
        v.proprietaire.numero_telephone = payload.telephone.strip()

    db.commit()
    return {"ok": True}


# ------------------------------------------------------------
# 6) update repair by id
# ------------------------------------------------------------
@app.put("/reparations/{reparation_id}")
def update_reparation(reparation_id: int, payload: ReparationUpdate, db: Session = Depends(get_db)):
    r = db.query(Reparation).filter(Reparation.id == reparation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Réparation introuvable")

    if payload.date_visite is not None:
        r.date_visite = payload.date_visite
    if payload.probleme_signale is not None:
        r.probleme_signale = payload.probleme_signale.strip()
    if payload.reparation_effectuee is not None:
        r.reparation_effectuee = payload.reparation_effectuee.strip()
    if payload.diagnostic is not None:
        r.diagnostic = payload.diagnostic.strip() if payload.diagnostic else None
    if payload.prix is not None:
        r.prix = payload.prix
    if payload.statut is not None:
        r.statut = payload.statut.strip()

    db.commit()
    return {"ok": True}


# ------------------------------------------------------------
# 7) delete repair
# ------------------------------------------------------------
@app.delete("/reparations/{reparation_id}")
def delete_reparation(reparation_id: int, db: Session = Depends(get_db)):
    r = db.query(Reparation).filter(Reparation.id == reparation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Réparation introuvable")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------
# 8) delete car (and its repairs)
# ------------------------------------------------------------
@app.delete("/voitures/by-numero-serie/{numero_serie}")
def delete_voiture(numero_serie: str, db: Session = Depends(get_db)):
    numero_serie = numero_serie.strip()
    v = db.query(Voiture).filter(Voiture.matricule == numero_serie).first()
    if not v:
        raise HTTPException(status_code=404, detail="Voiture introuvable")

    db.delete(v)
    db.commit()
    return {"ok": True}
