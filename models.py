from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Serveur(Base):
    __tablename__ = "serveurs"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, index=True)
    adresse_ip = Column(String, unique=True, index=True)
    utilisateur_ssh = Column(String)
    port_ssh = Column(Integer, default=22)
    chemin_cle_privee = Column(String, nullable=True)
    mot_de_passe = Column(String, nullable=True)

class LogExecution(Base):
    __tablename__ = "logs_execution"
    id = Column(Integer, primary_key=True, index=True)
    serveur_id = Column(Integer, ForeignKey("serveurs.id"))
    date_execution = Column(DateTime, default=datetime.datetime.utcnow)
    script = Column(Text)
    stdout = Column(Text)
    stderr = Column(Text)
    error = Column(Text)
    serveur = relationship("Serveur")

class TachePlanifiee(Base):
    __tablename__ = "taches_planifiees"
    id = Column(Integer, primary_key=True, index=True)
    serveur_id = Column(Integer, ForeignKey("serveurs.id"))
    script = Column(Text)
    date_execution = Column(DateTime)  # Prochaine exécution
    recurrence = Column(String, nullable=True)  # ex: 'daily', 'weekly', 'none'
    statut = Column(String, default="active")  # active, done, error, etc.
    dernier_run = Column(DateTime, nullable=True)
    serveur = relationship("Serveur") 