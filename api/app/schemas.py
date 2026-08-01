from datetime import datetime
from pydantic import BaseModel, Field


class DemandeConnexion(BaseModel):
    email: str
    mot_de_passe: str


class ReponseToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EnseignantConnecte(BaseModel):
    id: str
    nom: str
    prenom: str
    etablissement_id: str | None


class ExerciceEnAttente(BaseModel):
    id: str
    theme: str
    sous_theme: str | None
    niveau: str
    matiere: str
    difficulte: str
    enonce: str
    corrige: str
    etapes: list[str]
    contexte: str | None
    tags: list[str]
    source: str
    validation_ia: bool
    created_at: datetime


class ModificationExercice(BaseModel):
    """Corrections apportées par l'enseignant avant validation — tous les
    champs sont optionnels : on ne modifie que ce qui doit changer."""
    enonce: str | None = None
    corrige: str | None = None
    etapes: list[str] | None = None
    difficulte: str | None = None


class RejetExercice(BaseModel):
    motif: str = Field(..., min_length=5, description="Raison du rejet — obligatoire, "
                        "sert à améliorer les prompts/templates du pipeline")


class EleveConnecte(BaseModel):
    id: str
    nom: str
    prenom: str
    classe_id: str
    niveau_id: str


class ExerciceDisponible(BaseModel):
    """Vue élève d'un exercice : PAS de corrigé ni d'étapes tant que
    l'élève ne l'a pas explicitement révélé — évite de gâcher l'auto-évaluation
    en affichant la réponse dans la même requête que l'énoncé."""
    id: str
    matiere: str
    theme: str
    sous_theme: str | None
    difficulte: str
    enonce: str
    contexte: str | None
    tags: list[str]


class CorrigeExercice(BaseModel):
    corrige: str
    etapes: list[str]


class DeclarationTentative(BaseModel):
    reussi: bool
    temps_passe_secondes: int | None = Field(None, ge=0)
    reponse_donnee: str | None = None


class TentativeEnregistree(BaseModel):
    id: str
    exercice_id: str
    reussi: bool
    created_at: datetime


class ResultatMatiere(BaseModel):
    matiere: str
    trimestre: int
    moyenne_sur_20: float
    nombre_notes: int


class DevoirAVenir(BaseModel):
    id: str
    titre: str
    matiere: str
    description: str | None
    date_limite: datetime


class NotificationEleve(BaseModel):
    id: str
    titre: str
    message: str
    type_notification: str
    lue: bool
    created_at: datetime


class DirectionConnecte(BaseModel):
    id: str
    nom: str
    prenom: str
    etablissement_id: str


class TableauDeBord(BaseModel):
    effectif_eleves: int
    effectif_enseignants: int
    nombre_classes: int
    taux_reussite_tentatives_pct: float | None
    moyenne_generale_etablissement: float | None
    montant_du_total: float
    montant_paye_total: float
    exercices_en_attente_validation: int


class ValidationsEnAttenteParMatiere(BaseModel):
    matiere: str
    niveau: str
    nombre_en_attente: int
    plus_ancien: datetime | None


class ActiviteEnseignant(BaseModel):
    enseignant: str
    email: str
    nombre_classes_affectees: int
    nombre_exercices_valides: int
    nombre_exercices_rejetes: int


class MoyenneClasse(BaseModel):
    classe: str
    matiere: str
    moyenne_sur_20: float
    effectif_note: int


class PaiementEnRetard(BaseModel):
    eleve_nom: str
    eleve_prenom: str
    classe: str
    montant_du: float
    montant_paye: float
    montant_restant: float
    date_echeance: datetime | None


class AdministratifConnecte(BaseModel):
    id: str
    nom: str
    prenom: str
    etablissement_id: str


class AdminPlateformeConnecte(BaseModel):
    id: str
    nom: str
    prenom: str
    # Pas d'etablissement_id : par construction, un admin plateforme n'est
    # rattaché à aucun établissement en particulier — il supervise toute
    # la plateforme (voir utilisateurs.etablissement_id, nullable pour ce rôle).


class CreationEleve(BaseModel):
    email: str
    nom: str
    prenom: str
    classe_id: str
    matricule: str | None = None


class CreationEnseignant(BaseModel):
    email: str
    nom: str
    prenom: str
    specialite: str | None = None
    affectations: list[dict] = Field(default_factory=list,
                                       description="Liste de {classe_id, matiere_id}")


class CompteCree(BaseModel):
    """Le mot de passe en clair n'est renvoyé qu'UNE SEULE FOIS, à la création
    — il n'est jamais stocké ni récupérable ensuite, seul son hash l'est."""
    id: str
    email: str
    mot_de_passe_provisoire: str


class UtilisateurResume(BaseModel):
    id: str
    nom: str
    prenom: str
    email: str | None
    role: str
    actif: bool
    classe: str | None = None


class GenerationBulletins(BaseModel):
    classe_id: str
    trimestre: int = Field(..., ge=1, le=3)


class BulletinGenere(BaseModel):
    id: str
    eleve_id: str
    eleve_nom: str
    moyenne_generale: float | None
    rang_classe: int | None


class DiffusionNotification(BaseModel):
    titre: str
    message: str
    type_notification: str = "info"
    classe_id: str | None = None
    utilisateur_id: str | None = None
    inclure_parents: bool = True


class DiffusionResultat(BaseModel):
    nombre_notifications_envoyees: int


class EncaissementPaiement(BaseModel):
    montant: float = Field(..., gt=0)


class PaiementMisAJour(BaseModel):
    id: str
    montant_du: float
    montant_paye: float
    statut: str


class ParentConnecte(BaseModel):
    id: str
    nom: str
    prenom: str


class EnfantResume(BaseModel):
    eleve_id: str
    nom: str
    prenom: str
    classe: str
    niveau: str
    etablissement: str


class TableauDeBordEnfant(BaseModel):
    moyenne_generale: float | None
    nombre_absences: int
    nombre_retards: int
    dernieres_notes: list[dict]


class BulletinParent(BaseModel):
    trimestre: int
    moyenne_generale: float | None
    rang_classe: int | None
    fichier_pdf_url: str | None
    genere_le: datetime | None


class AbsenceParent(BaseModel):
    date_absence: datetime
    type_absence: str
    justifie: bool
    motif: str | None


class PaiementParent(BaseModel):
    id: str
    montant_du: float
    montant_paye: float
    date_echeance: datetime | None
    statut: str


class DevoirParent(BaseModel):
    titre: str
    matiere: str
    date_limite: datetime


class DepotCours(BaseModel):
    titre: str
    classe_id: str
    matiere_id: str
    contenu_texte: str | None = None
    fichier_url: str | None = None
    date_seance: str | None = None


class RessourceGeneree(BaseModel):
    type_ressource: str
    statut: str
    contenu: dict


class CoursResume(BaseModel):
    id: str
    titre: str
    matiere: str
    classe: str
    created_at: datetime
    nombre_ressources_validees: int
    nombre_ressources_total: int


class CoursDetail(BaseModel):
    id: str
    titre: str
    matiere: str
    classe: str
    contenu_texte: str | None
    created_at: datetime
    ressources: list[dict]


class ModificationRessource(BaseModel):
    contenu: dict | None = None
    statut: str | None = None


class ClasseEnseignant(BaseModel):
    classe_id: str
    matiere_id: str
    nom: str
    niveau_id: str
    niveau: str
    matiere: str
    etablissement_nom: str
    effectif: int
    moyenne_classe: float | None


class EleveResume(BaseModel):
    eleve_id: str
    nom: str
    prenom: str
    matricule: str | None
    moyenne: float | None
    nombre_absences: int


class NoteDetail(BaseModel):
    id: str
    valeur: float
    bareme: float
    type_evaluation: str
    trimestre: int
    created_at: datetime


class AbsenceDetail(BaseModel):
    id: str
    date_absence: str
    type_absence: str
    justifie: bool
    motif: str | None


class CreationNote(BaseModel):
    matiere_id: str
    valeur: float = Field(..., ge=0)
    bareme: float = Field(20, gt=0)
    type_evaluation: str = "controle"
    trimestre: int = Field(..., ge=1, le=3)


class CreationAbsence(BaseModel):
    date_absence: str
    type_absence: str = "absence"
    justifie: bool = False
    motif: str | None = None


class ClasseResume(BaseModel):
    id: str
    nom: str
    niveau: str


# ---------------------------------------------------------------------------
# Structure scolaire (années scolaires, cycles, niveaux, classes) — jusqu'ici
# toujours créée à la main en SQL, jamais via l'interface (TODO.md point 3).
# ---------------------------------------------------------------------------

class AnneeScolaireResume(BaseModel):
    id: str
    libelle: str
    date_debut: str
    date_fin: str
    est_active: bool


class CreationAnneeScolaire(BaseModel):
    libelle: str
    date_debut: str
    date_fin: str


class CycleResume(BaseModel):
    id: str
    nom: str
    ordre: int


class CreationCycle(BaseModel):
    nom: str
    ordre: int = 0


class NiveauResume(BaseModel):
    id: str
    nom: str
    ordre: int
    cycle_id: str
    cycle_nom: str


class CreationNiveau(BaseModel):
    cycle_id: str
    nom: str
    ordre: int = 0


class CreationClasse(BaseModel):
    niveau_id: str
    nom: str


class MatiereResume(BaseModel):
    id: str
    nom: str


class PaiementAdmin(BaseModel):
    id: str
    eleve_nom: str
    eleve_prenom: str
    classe: str
    montant_du: float
    montant_paye: float
    statut: str
    date_echeance: str | None


class CreationParent(BaseModel):
    email: str
    nom: str
    prenom: str
    eleve_ids: list[str] = Field(..., min_length=1, description="Au moins un enfant à lier")


class EtablissementInfo(BaseModel):
    id: str
    nom: str
    pays: str
    ville: str | None
    logo_url: str | None
    reglement_url: str | None


class ModificationEtablissement(BaseModel):
    nom: str | None = None
    ville: str | None = None


class ReferentielPedagogique(BaseModel):
    id: str
    niveau_id: str
    niveau: str
    matiere_id: str
    matiere: str
    programme_officiel: str
    manuel_titre: str | None
    manuel_editeur: str | None
    manuel_edition: str | None


class CreationReferentiel(BaseModel):
    niveau_id: str
    matiere_id: str
    programme_officiel: str
    manuel_titre: str | None = None
    manuel_editeur: str | None = None
    manuel_edition: str | None = None


class ChapitreCalendrier(BaseModel):
    id: str
    mois: str
    chapitre_titre: str
    competences: list[str]
    ordre: int


class CreationChapitre(BaseModel):
    referentiel_id: str
    mois: str  # 'YYYY-MM-DD' (premier jour du mois)
    chapitre_titre: str
    competences: list[str] = Field(default_factory=list)
    ordre: int = 0


class DocumentPedagogique(BaseModel):
    id: str
    type_document: str
    niveau: str | None
    matiere: str | None
    titre: str
    nombre_pages: int | None
    statut: str
    erreur_traitement: str | None
    nombre_passages: int
    est_proprietaire: bool = True
    # True par défaut (cas programme_officiel, où la notion de partage ne
    # s'applique pas) ; pour notes_cours, calculé côté serveur — False
    # signifie "document partagé avec vous par un collègue", en lecture
    # seule (pas de suppression, pas de re-partage possible).


class PassageRecherche(BaseModel):
    extrait: str
    similarite: float


class ResultatLigneImport(BaseModel):
    ligne: int
    email: str | None
    statut: str  # 'cree' | 'erreur'
    mot_de_passe_provisoire: str | None = None
    erreur: str | None = None


class RapportImport(BaseModel):
    total_lignes: int
    nombre_crees: int
    nombre_erreurs: int
    resultats: list[ResultatLigneImport]


class ExerciceValide(BaseModel):
    id: str
    statut: str
    valide_par_id: str
    date_validation: datetime


# ---------------------------------------------------------------------------
# Admin Plateforme
# ---------------------------------------------------------------------------

class EtablissementResume(BaseModel):
    id: str
    nom: str
    pays: str
    ville: str | None
    niveau_abonnement: str
    actif: bool
    created_at: datetime
    nombre_utilisateurs: int
    nombre_eleves: int


class CreationEtablissement(BaseModel):
    nom: str
    pays: str
    ville: str | None = None
    email_contact: str | None = None
    telephone_contact: str | None = None
    niveau_abonnement: str = "starter"
    # Premier compte administratif de l'établissement, créé dans la même
    # opération — sans lui, personne ne pourrait se connecter pour gérer
    # la nouvelle école une fois créée.
    admin_email: str
    admin_nom: str
    admin_prenom: str


class EtablissementCree(BaseModel):
    etablissement: EtablissementResume
    compte_admin: CompteCree


class ExerciceBiblioCommune(BaseModel):
    id: str
    niveau: str
    matiere: str
    theme: str
    difficulte: str
    statut: str
    source: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Enseignant indépendant : auto-inscription, invitations, génération libre
# ---------------------------------------------------------------------------

class InscriptionEnseignant(BaseModel):
    email: str
    mot_de_passe: str
    nom: str
    prenom: str
    specialite: str | None = None


class InvitationEnvoyee(BaseModel):
    id: str
    enseignant_email: str
    classe_nom: str | None = None
    matiere_nom: str | None = None
    statut: str
    created_at: datetime


class InvitationRecue(BaseModel):
    id: str
    etablissement_nom: str
    classe_nom: str | None = None
    matiere_nom: str | None = None
    statut: str
    created_at: datetime


class DemandeGenerationLibre(BaseModel):
    niveau: str
    # Texte libre, PAS de niveau_id : contrairement à matieres (globale),
    # niveaux est une table propre à chaque établissement (via cycles). Un
    # enseignant indépendant n'a accès à aucun niveau_id valide — voir
    # l'incident du 31/07 sur ce même sujet (Collège Vogt, TODO.md point 3).
    matiere_id: str
    theme: str


class ExerciceGenereLibre(BaseModel):
    theme: str
    sous_theme: str | None
    enonce: str
    corrige: str
    etapes: list[str]
    contexte: str | None
    tags: list[str]
    avertissement: str = "Contenu généré par IA, non relu par un humain — à vérifier avant toute utilisation en classe."
