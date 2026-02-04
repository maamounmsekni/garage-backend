from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Proprietaire(Base):
    __tablename__ = "proprietaires"

    id = Column(Integer, primary_key=True, index=True)
    nom_complet = Column(Text, nullable=False)
    numero_telephone = Column(Text, nullable=False)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    voitures = relationship("Voiture", back_populates="proprietaire")


class TypeVoiture(Base):
    __tablename__ = "types_voiture"

    id = Column(Integer, primary_key=True, index=True)
    nom_type = Column(Text, nullable=False)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    voitures = relationship("Voiture", back_populates="type_voiture")


class Voiture(Base):
    __tablename__ = "voitures"

    id = Column(Integer, primary_key=True, index=True)
    id_proprietaire = Column(Integer, ForeignKey("proprietaires.id", ondelete="RESTRICT"), nullable=False)
    id_type_voiture = Column(Integer, ForeignKey("types_voiture.id", ondelete="RESTRICT"), nullable=False)

    matricule = Column(Text, nullable=False, unique=True)
    remarques = Column(Text, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    proprietaire = relationship("Proprietaire", back_populates="voitures")
    type_voiture = relationship("TypeVoiture", back_populates="voitures")
    reparations = relationship("Reparation", back_populates="voiture", cascade="all, delete-orphan")


class Reparation(Base):
    __tablename__ = "reparations"

    id = Column(Integer, primary_key=True, index=True)
    id_voiture = Column(Integer, ForeignKey("voitures.id", ondelete="CASCADE"), nullable=False)

    date_visite = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    probleme_signale = Column(Text, nullable=False)
    diagnostic = Column(Text, nullable=True)
    reparation_effectuee = Column(Text, nullable=False)

    prix = Column(Numeric(10, 2), nullable=True)
    statut = Column(String, nullable=False, default="EN_COURS")  # EN_COURS | TERMINEE | ANNULEE
    cree_le = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    voiture = relationship("Voiture", back_populates="reparations")
