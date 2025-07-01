# Utilise une image Python officielle légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt ./

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Exposer le port de l'application
EXPOSE 8000

# Commande de lancement (production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 