from fastapi import FastAPI, Depends, HTTPException, Body, Form
from sqlalchemy.orm import Session
from database import init_db, SessionLocal
from models import Serveur, LogExecution, TachePlanifiee
from pydantic import BaseModel
from typing import List
import paramiko
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import hashlib
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import threading
import time
from datetime import datetime, timedelta
import subprocess

app = FastAPI()

init_db()

# Configuration Jinja2 et fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dépendance pour obtenir une session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schémas Pydantic
class ServeurCreate(BaseModel):
    nom: str
    adresse_ip: str
    utilisateur_ssh: str
    port_ssh: int = 22
    chemin_cle_privee: str = None
    mot_de_passe: str = None

class ServeurRead(BaseModel):
    id: int
    nom: str
    adresse_ip: str
    utilisateur_ssh: str
    port_ssh: int
    chemin_cle_privee: str = None
    mot_de_passe: str = None
    class Config:
        orm_mode = True

class ScriptExecutionRequest(BaseModel):
    script: str  # Le script shell à exécuter

# --- Configuration utilisateur admin (à améliorer pour la prod) ---
ADMIN_USERNAME = "admin"
# Mot de passe haché SHA256 (exemple pour 'collecteur2024')
ADMIN_PASSWORD_HASH = hashlib.sha256("collecteur2024".encode()).hexdigest()

app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")

@app.get("/")
def lire_racine():
    return {"message": "Bienvenue sur Le Collecteur !"}

@app.post("/serveurs/", response_model=ServeurRead)
def creer_serveur(serveur: ServeurCreate, db: Session = Depends(get_db)):
    db_serveur = Serveur(**serveur.dict())
    db.add(db_serveur)
    try:
        db.commit()
        db.refresh(db_serveur)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erreur lors de la création du serveur : " + str(e))
    return db_serveur

@app.get("/serveurs/", response_model=List[ServeurRead])
def lister_serveurs(db: Session = Depends(get_db)):
    return db.query(Serveur).all()

@app.delete("/serveurs/{serveur_id}")
def supprimer_serveur(serveur_id: int, db: Session = Depends(get_db)):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if not serveur:
        raise HTTPException(status_code=404, detail="Serveur non trouvé")
    db.delete(serveur)
    db.commit()
    return {"ok": True}

@app.post("/serveurs/{serveur_id}/executer_script")
def executer_script_ssh(serveur_id: int, data: ScriptExecutionRequest = Body(...), db: Session = Depends(get_db)):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if not serveur:
        raise HTTPException(status_code=404, detail="Serveur non trouvé")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_args = {
            "hostname": serveur.adresse_ip,
            "port": serveur.port_ssh,
            "username": serveur.utilisateur_ssh,
        }
        if serveur.chemin_cle_privee:
            connect_args["key_filename"] = serveur.chemin_cle_privee
        elif serveur.mot_de_passe:
            connect_args["password"] = serveur.mot_de_passe
        ssh.connect(**connect_args)
        stdin, stdout, stderr = ssh.exec_command(data.script)
        sortie = stdout.read().decode()
        erreur = stderr.read().decode()
        ssh.close()
        return {"stdout": sortie, "stderr": erreur}
    except Exception as e:
        return {"error": str(e)}

# --- Page de connexion ---
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login_action(request: Request, username: str = Form(...), password: str = Form(...)):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
        request.session["user"] = username
        return RedirectResponse(url="/serveurs_html", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Identifiants invalides"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# --- Dépendance de sécurité ---
def require_login(request: Request):
    if request.session.get("user") != ADMIN_USERNAME:
        raise HTTPException(status_code=303, detail="Non authentifié", headers={"Location": "/login"})

# --- Utilitaire pour notifications ---
def set_notification(request, message, type_="success"):
    request.session["notification"] = {"message": message, "type": type_}

def pop_notification(request):
    notif = request.session.pop("notification", None)
    return notif

# --- Protection des routes web ---
from fastapi import Depends

@app.get("/serveurs_html")
def page_serveurs(request: Request, db: Session = Depends(get_db), user: str = Depends(require_login)):
    serveurs = db.query(Serveur).all()
    notif = pop_notification(request)
    return templates.TemplateResponse("serveurs.html", {"request": request, "serveurs": serveurs, "notification": notif})

@app.post("/ajouter_serveur_html")
def ajouter_serveur_html(
    nom: str = Form(...),
    adresse_ip: str = Form(...),
    utilisateur_ssh: str = Form(...),
    port_ssh: int = Form(...),
    chemin_cle_privee: str = Form(None),
    mot_de_passe: str = Form(None),
    db: Session = Depends(get_db),
    user: str = Depends(require_login),
    request: Request = None
):
    nouveau_serveur = Serveur(
        nom=nom,
        adresse_ip=adresse_ip,
        utilisateur_ssh=utilisateur_ssh,
        port_ssh=port_ssh,
        chemin_cle_privee=chemin_cle_privee,
        mot_de_passe=mot_de_passe
    )
    db.add(nouveau_serveur)
    try:
        db.commit()
        set_notification(request, "Serveur ajouté avec succès.", "success")
    except Exception:
        db.rollback()
        set_notification(request, "Erreur lors de l'ajout du serveur.", "error")
    return RedirectResponse(url="/serveurs_html", status_code=303)

@app.post("/supprimer_serveur_html")
def supprimer_serveur_html(serveur_id: int = Form(...), db: Session = Depends(get_db), user: str = Depends(require_login), request: Request = None):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if serveur:
        db.delete(serveur)
        db.commit()
        set_notification(request, "Serveur supprimé.", "success")
    else:
        set_notification(request, "Serveur introuvable.", "error")
    return RedirectResponse(url="/serveurs_html", status_code=303)

@app.get("/editer_serveur_html")
def editer_serveur_html(request: Request, serveur_id: int, db: Session = Depends(get_db), user: str = Depends(require_login)):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    return templates.TemplateResponse("editer_serveur.html", {"request": request, "serveur": serveur})

@app.post("/editer_serveur_html")
def enregistrer_edition_serveur_html(
    serveur_id: int = Form(...),
    nom: str = Form(...),
    adresse_ip: str = Form(...),
    utilisateur_ssh: str = Form(...),
    port_ssh: int = Form(...),
    chemin_cle_privee: str = Form(None),
    mot_de_passe: str = Form(None),
    db: Session = Depends(get_db),
    user: str = Depends(require_login),
    request: Request = None
):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if serveur:
        serveur.nom = nom
        serveur.adresse_ip = adresse_ip
        serveur.utilisateur_ssh = utilisateur_ssh
        serveur.port_ssh = port_ssh
        serveur.chemin_cle_privee = chemin_cle_privee
        serveur.mot_de_passe = mot_de_passe
        try:
            db.commit()
            set_notification(request, "Serveur modifié avec succès.", "success")
        except Exception:
            db.rollback()
            set_notification(request, "Erreur lors de la modification.", "error")
    else:
        set_notification(request, "Serveur introuvable.", "error")
    return RedirectResponse(url="/serveurs_html", status_code=303)

@app.post("/executer_script_html")
def executer_script_html(
    serveur_id: int = Form(...),
    script: str = Form(...),
    db: Session = Depends(get_db),
    request: Request = None,
    user: str = Depends(require_login)
):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    resultat = None
    log = LogExecution(serveur_id=serveur_id, script=script)
    if serveur:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_args = {
                "hostname": serveur.adresse_ip,
                "port": serveur.port_ssh,
                "username": serveur.utilisateur_ssh,
            }
            if serveur.chemin_cle_privee:
                connect_args["key_filename"] = serveur.chemin_cle_privee
            elif serveur.mot_de_passe:
                connect_args["password"] = serveur.mot_de_passe
            ssh.connect(**connect_args)
            stdin, stdout, stderr = ssh.exec_command(script)
            sortie = stdout.read().decode()
            erreur = stderr.read().decode()
            log.stdout = sortie
            log.stderr = erreur
            resultat = {"stdout": sortie, "stderr": erreur}
            ssh.close()
            set_notification(request, "Script exécuté avec succès.", "success")
        except Exception as e:
            log.error = str(e)
            resultat = {"error": str(e)}
            set_notification(request, f"Erreur lors de l'exécution : {str(e)}", "error")
    db.add(log)
    db.commit()
    serveurs = db.query(Serveur).all()
    notif = pop_notification(request)
    return templates.TemplateResponse("serveurs.html", {"request": request, "serveurs": serveurs, "resultat": resultat, "serveur_id_resultat": serveur_id, "notification": notif})

@app.get("/logs_html")
def logs_html(request: Request, serveur_id: int, db: Session = Depends(get_db), user: str = Depends(require_login)):
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    logs = db.query(LogExecution).filter(LogExecution.serveur_id == serveur_id).order_by(LogExecution.date_execution.desc()).all()
    return templates.TemplateResponse("logs.html", {"request": request, "serveur": serveur, "logs": logs})

@app.get("/dashboard_html")
def dashboard_html(request: Request, db: Session = Depends(get_db), user: str = Depends(require_login)):
    nb_serveurs = db.query(Serveur).count()
    nb_exec = db.query(LogExecution).count()
    derniers_logs = db.query(LogExecution).order_by(LogExecution.date_execution.desc()).limit(5).all()
    # Calcul du nombre d'échecs automatiques récents
    nb_alertes = db.query(LogExecution).filter(LogExecution.error != None, LogExecution.error.like("%automatique%"), LogExecution.date_execution >= datetime.utcnow()-timedelta(days=1)).count()
    notif_alerte = None
    if nb_alertes > 0:
        notif_alerte = f"{nb_alertes} tâche(s) planifiée(s) ont échoué ces dernières 24h."
    return templates.TemplateResponse("dashboard.html", {"request": request, "nb_serveurs": nb_serveurs, "nb_exec": nb_exec, "derniers_logs": derniers_logs, "nb_alertes": nb_alertes, "notif_alerte": notif_alerte})

@app.get("/taches_html")
def taches_html(request: Request, db: Session = Depends(get_db), user: str = Depends(require_login)):
    taches = db.query(TachePlanifiee).order_by(TachePlanifiee.date_execution).all()
    serveurs = db.query(Serveur).all()
    notif = pop_notification(request)
    return templates.TemplateResponse("taches.html", {"request": request, "taches": taches, "serveurs": serveurs, "notification": notif})

@app.post("/taches_html")
def ajouter_tache_html(
    serveur_id: int = Form(...),
    script: str = Form(...),
    date_execution: str = Form(...),
    recurrence: str = Form(None),
    db: Session = Depends(get_db),
    user: str = Depends(require_login),
    request: Request = None
):
    from datetime import datetime
    try:
        date_exec = datetime.strptime(date_execution, "%Y-%m-%dT%H:%M")
        tache = TachePlanifiee(
            serveur_id=serveur_id,
            script=script,
            date_execution=date_exec,
            recurrence=recurrence or None,
            statut="active"
        )
        db.add(tache)
        db.commit()
        set_notification(request, "Tâche planifiée ajoutée.", "success")
    except Exception as e:
        db.rollback()
        set_notification(request, f"Erreur : {e}", "error")
    return RedirectResponse(url="/taches_html", status_code=303)

@app.post("/supprimer_tache_html")
def supprimer_tache_html(tache_id: int = Form(...), db: Session = Depends(get_db), user: str = Depends(require_login), request: Request = None):
    tache = db.query(TachePlanifiee).filter(TachePlanifiee.id == tache_id).first()
    if tache:
        db.delete(tache)
        db.commit()
        set_notification(request, "Tâche supprimée.", "success")
    else:
        set_notification(request, "Tâche introuvable.", "error")
    return RedirectResponse(url="/taches_html", status_code=303)

# --- SCHEDULER POUR LES TÂCHES PLANIFIÉES ---
scheduler = BackgroundScheduler()

def executer_tache_planifiee(tache_id):
    db = SessionLocal()
    tache = db.query(TachePlanifiee).filter(TachePlanifiee.id == tache_id).first()
    if not tache or tache.statut != "active":
        db.close()
        return
    serveur = db.query(Serveur).filter(Serveur.id == tache.serveur_id).first()
    log = LogExecution(serveur_id=tache.serveur_id, script=tache.script, error=None)
    try:
        log.origine = "automatique"
    except Exception:
        pass
    if serveur:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_args = {
                "hostname": serveur.adresse_ip,
                "port": serveur.port_ssh,
                "username": serveur.utilisateur_ssh,
            }
            if serveur.chemin_cle_privee:
                connect_args["key_filename"] = serveur.chemin_cle_privee
            elif serveur.mot_de_passe:
                connect_args["password"] = serveur.mot_de_passe
            ssh.connect(**connect_args)
            stdin, stdout, stderr = ssh.exec_command(tache.script)
            sortie = stdout.read().decode()
            erreur = stderr.read().decode()
            log.stdout = sortie
            log.stderr = erreur
            tache.dernier_run = datetime.utcnow()
            db.commit()
            ssh.close()
        except Exception as e:
            log.error = f"Erreur automatique : {str(e)}"
            tache.dernier_run = datetime.utcnow()
            tache.statut = "error"
            db.commit()
    db.add(log)
    db.commit()
    # Gérer la récurrence
    if tache.recurrence == "daily":
        tache.date_execution += timedelta(days=1)
        tache.statut = "active"
        db.commit()
    elif tache.recurrence == "weekly":
        tache.date_execution += timedelta(weeks=1)
        tache.statut = "active"
        db.commit()
    else:
        tache.statut = "done"
        db.commit()
    db.close()

def verifier_et_planifier_taches():
    db = SessionLocal()
    now = datetime.utcnow()
    taches = db.query(TachePlanifiee).filter(TachePlanifiee.statut == "active").all()
    for t in taches:
        if t.date_execution <= now:
            # Planifie l'exécution immédiate si pas déjà planifiée
            scheduler.add_job(executer_tache_planifiee, args=[t.id], trigger=DateTrigger(run_date=now))
    db.close()

scheduler.add_job(verifier_et_planifier_taches, IntervalTrigger(minutes=1))
scheduler.start()

@app.post("/afficher_mot_de_passe/{serveur_id}")
def afficher_mot_de_passe(serveur_id: int, password: str = Form(...), db: Session = Depends(get_db), request: Request = None):
    import hashlib
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != ADMIN_PASSWORD_HASH:
        return JSONResponse({"success": False, "message": "Mot de passe de session incorrect."}, status_code=401)
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if not serveur:
        return JSONResponse({"success": False, "message": "Serveur introuvable."}, status_code=404)
    return {"success": True, "mot_de_passe": serveur.mot_de_passe or ""}

@app.get("/ping/{serveur_id}")
def ping_serveur(serveur_id: int, db: Session = Depends(get_db)):
    import platform
    serveur = db.query(Serveur).filter(Serveur.id == serveur_id).first()
    if not serveur:
        return JSONResponse({"success": False, "message": "Serveur introuvable.", "latency_ms": None, "ip": None, "error": "not_found"}, status_code=404)
    ip = serveur.adresse_ip
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    try:
        # On ping une seule fois, timeout 2s
        result = subprocess.run(["ping", param, "1", ip], capture_output=True, text=True, timeout=3)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            # Extraction du temps de réponse
            import re
            match = re.search(r'time[=<]([0-9]+)ms', output)
            latency = int(match.group(1)) if match else None
            return {"success": True, "message": f"Réponse en {latency if latency is not None else '?'} ms", "latency_ms": latency, "ip": ip, "error": None}
        else:
            return {"success": False, "message": "Timeout ou hôte injoignable", "latency_ms": None, "ip": ip, "error": output.strip()}
    except Exception as e:
        return {"success": False, "message": "Erreur lors du ping", "latency_ms": None, "ip": ip, "error": str(e)} 