import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# En prod, cette clé DOIT venir d'une variable d'environnement gérée par le
# secret manager de l'hébergeur (jamais committée) — la valeur par défaut
# ici n'existe que pour que le code tourne en développement local.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-ne-jamais-utiliser-en-prod")
ALGORITHME = "HS256"
DUREE_TOKEN_MINUTES = 60 * 8  # 8h — durée d'une journée de classe


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    # bcrypt directement plutôt que passlib : passlib.CryptContext a un bug
    # de compatibilité connu avec les versions récentes du paquet bcrypt
    # (AttributeError sur bcrypt.__about__) — mieux vaut l'appel direct,
    # plus simple et sans cette dépendance fragile.
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))


def creer_token_acces(utilisateur_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(minutes=DUREE_TOKEN_MINUTES)
    payload = {"sub": str(utilisateur_id), "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHME)


def decoder_token(token: str) -> str:
    """Retourne l'utilisateur_id contenu dans le token, ou lève jwt.PyJWTError."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHME])
    return payload["sub"]
