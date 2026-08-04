"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GraduationCap, Lock, Mail, ChevronLeft, ChevronRight, ChevronDown,
  Check, X as XIcon, Pencil, Bot, CalculatorIcon, LogOut, Bell,
  Calculator, FlaskConical, Leaf, Landmark, Languages, Clock, History,
  FileText, Wand2, Sparkles, Trash2, Plus, BookMarked,
  ListChecks, HelpCircle, NotebookPen, ScrollText, Loader2,
  Users, TrendingUp, CalendarX, AlertTriangle, Upload, Share2, UserPlus,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Configuration API                                                  */
/* ------------------------------------------------------------------ */

// À adapter à la main selon où tourne votre backend (dev local, VPS...).
// Ex : "http://89.116.111.3:8000" une fois l'API déployée sur le serveur.
const API_BASE_URL = "http://89.116.111.3:8000";

class ErreurApi extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function apiFetch(path, { method = "GET", token, body, params } = {}) {
  let url = `${API_BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const estFormData = typeof FormData !== "undefined" && body instanceof FormData;
  let reponse;
  try {
    reponse = await fetch(url, {
      method,
      // Pour un FormData, on NE MET PAS Content-Type : le navigateur doit
      // fixer lui-même la frontière multipart (boundary), sinon la requête
      // est mal formée et l'API ne peut pas parser le fichier envoyé.
      headers: {
        ...(body && !estFormData ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? (estFormData ? body : JSON.stringify(body)) : undefined,
    });
  } catch (e) {
    throw new ErreurApi(
      `Impossible de joindre l'API (${API_BASE_URL}). Vérifiez qu'elle tourne et que CORS est activé.`
    );
  }

  if (reponse.status === 204) return null;

  let donnees = null;
  try { donnees = await reponse.json(); } catch { /* corps vide */ }

  if (!reponse.ok) {
    const message = donnees?.detail || `Erreur ${reponse.status}`;
    throw new ErreurApi(typeof message === "string" ? message : JSON.stringify(message), reponse.status);
  }
  return donnees;
}

/* ------------------------------------------------------------------ */
/*  Constantes d'affichage (icônes/texture papier par matière — pas de */
/*  données métier, juste du style, donc toujours en dur ici)          */
/* ------------------------------------------------------------------ */

const ICONES_MATIERE = {
  "Mathématiques": { icon: Calculator, papier: "grille" },
  "Physique-Chimie": { icon: FlaskConical, papier: "grille" },
  "SVT": { icon: Leaf, papier: "lignes" },
  "Histoire-Géographie": { icon: Landmark, papier: "lignes" },
  "Français": { icon: Languages, papier: "lignes" },
};
function infoMatiere(nom) {
  return ICONES_MATIERE[nom] || { icon: FileText, papier: "lignes" };
}

const DIFFICULTE_LABEL = { facile: "Facile", moyen: "Moyen", difficile: "Difficile" };
const TRIMESTRES = [1, 2, 3];
const TYPES_EVALUATION = ["controle", "devoir", "examen", "participation"];
const TYPE_EVALUATION_LABEL = { controle: "Contrôle", devoir: "Devoir", examen: "Examen", participation: "Participation" };
const TYPES_RESSOURCE = [
  { key: "fiche_pedagogique", label: "Fiche pédagogique", icon: BookMarked },
  { key: "resume", label: "Résumé", icon: FileText },
  { key: "exercices", label: "Exercices", icon: ListChecks },
  { key: "qcm", label: "QCM", icon: HelpCircle },
  { key: "devoir", label: "Devoir", icon: NotebookPen },
  { key: "controle", label: "Contrôle", icon: ScrollText },
];

/* ------------------------------------------------------------------ */
/*  Styles injectés                                                    */
/* ------------------------------------------------------------------ */

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

  .eduai-root { font-family: 'IBM Plex Sans', sans-serif; }
  .eduai-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; }
  .eduai-mono { font-family: 'Space Mono', monospace; letter-spacing: 0.02em; }

  .eduai-paper-grille {
    background-image:
      linear-gradient(rgba(34,48,74,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(34,48,74,0.06) 1px, transparent 1px);
    background-size: 18px 18px;
  }
  .eduai-paper-lignes {
    background-image: repeating-linear-gradient(
      to bottom, transparent, transparent 23px, rgba(34,48,74,0.09) 24px
    );
    background-position: 0 14px;
  }

  .eduai-fade-in { animation: eduai-fade 320ms ease-out forwards; }
  @keyframes eduai-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  .eduai-spin { animation: eduai-spin 1.1s linear infinite; }
  @keyframes eduai-spin { to { transform: rotate(360deg); } }

  @media (prefers-reduced-motion: reduce) {
    .eduai-fade-in { animation: none !important; }
    .eduai-spin { animation-duration: 2.4s; }
  }

  .eduai-focus:focus-visible {
    outline: 2px solid #B08D57;
    outline-offset: 2px;
    border-radius: 6px;
  }

  .eduai-textarea { resize: vertical; line-height: 1.55; }
`;

/* ------------------------------------------------------------------ */
/*  Palette                                                             */
/* ------------------------------------------------------------------ */

const C = {
  fond: "#FAF8F3",
  surface: "#FFFFFF",
  surfaceOmbre: "0 12px 32px -16px rgba(34,48,74,0.16), 0 2px 8px -4px rgba(34,48,74,0.08)",
  ligne: "#E7E2D6",
  encre: "#22304A",
  encreDoux: "#5B6472",
  encreAttenue: "#8891A0",
  accent: "#B08D57",
  accentClair: "#C7A574",
  accentFonce: "#8F7140",
  rouge: "#A23E38",
  vert: "#3F7A5C",
  vertFond: "#E7F1EA",
  ambre: "#B0813A",
  ambreFond: "#F5EBD8",
  rougeFond: "#F3E1DF",
  bleuFond: "#E4EAF2",
};

function badgeColorForDifficulte(d) {
  if (d === "facile") return { bg: C.vertFond, fg: C.vert };
  if (d === "moyen") return { bg: C.ambreFond, fg: C.ambre };
  return { bg: C.rougeFond, fg: C.rouge };
}
function badgeSource(source) {
  if (source === "python_genere") return { label: "Calcul vérifié", bg: C.vertFond, fg: C.vert, Icon: CalculatorIcon };
  return { label: "À vérifier — IA", bg: C.ambreFond, fg: C.ambre, Icon: Bot };
}

/* ------------------------------------------------------------------ */
/*  Petits composants partagés                                         */
/* ------------------------------------------------------------------ */

function Chargement({ label = "Chargement..." }) {
  return (
    <div className="flex items-center gap-2 py-10 justify-center" style={{ color: C.encreDoux }}>
      <Loader2 size={16} className="eduai-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

function BandeauErreur({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-lg px-4 py-3 mb-4 flex items-start gap-2 text-sm" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
      <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function BandeauSucces({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-lg px-4 py-3 mb-4 flex items-start gap-2 text-sm" style={{ backgroundColor: C.vertFond, color: C.vert }}>
      <Check size={15} className="mt-0.5 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function ChipMatiere({ label, active, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className="eduai-focus flex items-center gap-1.5 whitespace-nowrap px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors border"
      style={{ backgroundColor: active ? C.encre : C.surface, color: active ? C.surface : C.encreDoux, borderColor: active ? C.encre : C.ligne }}
    >
      {Icon && <Icon size={13} />}
      {label}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Connexion                                                   */
/* ------------------------------------------------------------------ */

const PAYS_DISPONIBLES = [
  "Cameroun", "Sénégal", "Côte d'Ivoire", "République démocratique du Congo", "Bénin", "Togo", "Gabon",
];

function EcranConnexion({ onConnexion, onInscription, connexionEnCours, erreurConnexion }) {
  const [mode, setMode] = useState("connexion"); // "connexion" | "inscription"
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [pays, setPays] = useState("Cameroun");
  const [specialite, setSpecialite] = useState("");

  function soumettre(e) {
    e.preventDefault();
    if (mode === "connexion") onConnexion(email, motDePasse);
    else onInscription({ email, mot_de_passe: motDePasse, nom, prenom, pays, specialite: specialite || null });
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 eduai-root" style={{ backgroundColor: C.fond }}>
      <div className="w-full max-w-sm eduai-fade-in">
        <div className="flex items-center gap-2 mb-10 justify-center">
          <GraduationCap size={26} color={C.encre} strokeWidth={1.75} />
          <span className="eduai-display text-2xl" style={{ color: C.encre }}>
            ÉduAI <span style={{ color: C.accent }}>Afrique</span>
          </span>
        </div>

        <div className="rounded-2xl p-8 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Espace Enseignant</h1>
          <p className="text-sm mb-5" style={{ color: C.encreDoux }}>
            {mode === "connexion" ? "Connecte-toi pour préparer tes cours." : "Ton établissement n'est pas encore inscrit ? Crée un compte indépendant."}
          </p>

          <div className="flex gap-1 mb-6 rounded-lg p-1" style={{ backgroundColor: C.fond }}>
            <button type="button" onClick={() => setMode("connexion")}
              className="eduai-focus flex-1 rounded-md py-1.5 text-xs font-medium transition-colors"
              style={mode === "connexion" ? { backgroundColor: C.surface, color: C.encre, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" } : { color: C.encreAttenue }}>
              Se connecter
            </button>
            <button type="button" onClick={() => setMode("inscription")}
              className="eduai-focus flex-1 rounded-md py-1.5 text-xs font-medium transition-colors"
              style={mode === "inscription" ? { backgroundColor: C.surface, color: C.encre, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" } : { color: C.encreAttenue }}>
              Compte indépendant
            </button>
          </div>

          <BandeauErreur message={erreurConnexion} />

          <form onSubmit={soumettre} className="space-y-4">
            {mode === "inscription" && (
              <div className="grid grid-cols-2 gap-2">
                <input required value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom"
                  className="eduai-focus rounded-lg px-3.5 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
                <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom"
                  className="eduai-focus rounded-lg px-3.5 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
              </div>
            )}
            {mode === "inscription" && (
              <label className="block">
                <span className="text-xs font-medium mb-1.5 block" style={{ color: C.encreDoux }}>Pays</span>
                <select value={pays} onChange={(e) => setPays(e.target.value)}
                  className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
                  style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
                  {PAYS_DISPONIBLES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                <span className="text-[11px] mt-1 block" style={{ color: C.encreAttenue }}>
                  Détermine quel programme officiel sert de référence à vos générations.
                </span>
              </label>
            )}
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}>
                <Mail size={13} /> Adresse email
              </span>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="sophie.nguema@ecole.cm"
                className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
                style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}>
                <Lock size={13} /> Mot de passe
              </span>
              <input
                type="password" required value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)}
                placeholder="••••••••"
                className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
                style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}
              />
            </label>
            {mode === "inscription" && (
              <input value={specialite} onChange={(e) => setSpecialite(e.target.value)} placeholder="Spécialité (optionnel, ex : Mathématiques)"
                className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            )}

            <button
              type="submit" disabled={connexionEnCours}
              className="eduai-focus w-full flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold mt-2 transition-colors disabled:opacity-60"
              style={{ backgroundColor: C.encre, color: C.surface }}
            >
              {connexionEnCours && <Loader2 size={14} className="eduai-spin" />}
              {mode === "connexion" ? "Se connecter" : "Créer mon compte"}
            </button>
          </form>
          {mode === "inscription" && (
            <p className="text-xs mt-4" style={{ color: C.encreAttenue }}>
              Utilisable dès maintenant pour préparer tes cours en mode libre. Si ton établissement rejoint la plateforme plus tard, il pourra t'inviter à le rejoindre.
            </p>
          )}
        </div>

        <p className="text-center text-xs mt-6" style={{ color: C.encreAttenue }}>
          API : <span className="eduai-mono">{API_BASE_URL}</span>
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Barre de navigation                                                */
/* ------------------------------------------------------------------ */

function BarreNav({ vue, setVue, onDeconnexion, nombreEnAttente, nombreInvitations }) {
  const items = [
    { id: "accueil", label: "Accueil" },
    { id: "mes-cours", label: "Mes cours" },
    { id: "mes-classes", label: "Mes classes" },
    { id: "mes-documents", label: "Mes documents" },
    { id: "generation-libre", label: "Génération libre" },
    { id: "mes-credits", label: "Mes crédits" },
    { id: "invitations", label: "Invitations", badge: nombreInvitations },
    { id: "file", label: "À valider", badge: nombreEnAttente },
    { id: "historique", label: "Historique de validation" },
  ];
  return (
    <div
      className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b flex-wrap gap-y-2"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}
    >
      <button onClick={() => setVue("accueil")} className="eduai-focus flex items-center gap-2">
        <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
        <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>ÉduAI Afrique</span>
      </button>

      <nav className="flex items-center gap-4 overflow-x-auto">
        {items.map((it) => (
          <button
            key={it.id}
            onClick={() => setVue(it.id)}
            className="eduai-focus relative pb-1 text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
            style={{ color: vue === it.id ? C.encre : C.encreAttenue }}
          >
            {it.label}
            {!!it.badge && (
              <span className="eduai-mono text-[10px] px-1.5 rounded-full" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                {it.badge}
              </span>
            )}
            {vue === it.id && <span className="absolute left-0 right-0 -bottom-[15px] h-[2px]" style={{ backgroundColor: C.accent }} />}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-4">
        <button className="eduai-focus relative" aria-label="Notifications">
          <Bell size={17} color={C.encreDoux} />
        </button>
        <button onClick={onDeconnexion} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.encreDoux }}>
          <LogOut size={14} />
          <span className="hidden sm:inline">Déconnexion</span>
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Accueil                                                     */
/* ------------------------------------------------------------------ */

function EcranAccueil({ setVue, enAttente, historique, cours, classes }) {
  const valides = historique.filter((h) => h.statut === "valide").length;
  const rejetes = historique.filter((h) => h.statut === "rejete").length;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Bonjour !</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>Que veux-tu faire aujourd'hui ?</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <button
          onClick={() => setVue("deposer-cours")}
          className="eduai-focus text-left rounded-xl p-6 transition-transform hover:-translate-y-0.5"
          style={{ backgroundColor: C.encre, boxShadow: C.surfaceOmbre }}
        >
          <Wand2 size={20} color={C.accentClair} className="mb-3" />
          <p className="eduai-display text-lg mb-1" style={{ color: C.surface }}>Déposer un cours</p>
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.65)" }}>L'IA génère fiche, résumé, exercices, QCM, devoir et contrôle.</p>
        </button>

        <button
          onClick={() => setVue("mes-classes")}
          className="eduai-focus text-left rounded-xl p-6 border transition-transform hover:-translate-y-0.5"
          style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}
        >
          <Users size={20} color={C.accentFonce} className="mb-3" />
          <p className="eduai-display text-lg mb-1" style={{ color: C.encre }}>Mes classes</p>
          <p className="text-xs" style={{ color: C.encreDoux }}>{classes.length} classe{classes.length !== 1 ? "s" : ""}, notes et absences.</p>
        </button>

        <button
          onClick={() => setVue("mes-cours")}
          className="eduai-focus text-left rounded-xl p-6 border transition-transform hover:-translate-y-0.5"
          style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}
        >
          <BookMarked size={20} color={C.accentFonce} className="mb-3" />
          <p className="eduai-display text-lg mb-1" style={{ color: C.encre }}>Ma banque de cours</p>
          <p className="text-xs" style={{ color: C.encreDoux }}>{cours.length} cours déposés.</p>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <CarteStat label="En attente de relecture" valeur={enAttente.length} icon={Clock} accent />
        <CarteStat label="Validés cette session" valeur={valides} icon={Check} />
        <CarteStat label="Rejetés cette session" valeur={rejetes} icon={XIcon} />
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="eduai-display text-lg" style={{ color: C.encre }}>À relire en priorité</h2>
        <button onClick={() => setVue("file")} className="eduai-focus text-xs font-medium flex items-center gap-1" style={{ color: C.accentFonce }}>
          Voir toute la file <ChevronRight size={14} />
        </button>
      </div>

      <div className="space-y-3">
        {enAttente.slice(0, 3).map((ex) => (
          <div key={ex.id} className="rounded-xl px-5 py-4 flex items-center justify-between border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
            <div>
              <p className="text-sm font-semibold" style={{ color: C.encre }}>{ex.theme}</p>
              <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{ex.matiere} · {ex.niveau}</p>
            </div>
            <button onClick={() => setVue("file")} className="eduai-focus text-xs font-medium px-3 py-1.5 rounded-full" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
              Relire
            </button>
          </div>
        ))}
        {enAttente.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun exercice en attente — tout est à jour.</p>}
      </div>
    </div>
  );
}

function CarteStat({ label, valeur, icon: Icon, accent }) {
  return (
    <div className="rounded-xl p-5 border" style={{ backgroundColor: accent ? C.encre : C.surface, boxShadow: C.surfaceOmbre, borderColor: accent ? C.encre : C.ligne }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: accent ? "rgba(255,255,255,0.75)" : C.encreDoux }}>{label}</span>
        <Icon size={15} color={accent ? C.accentClair : C.encreAttenue} />
      </div>
      <p className="eduai-display text-2xl" style={{ color: accent ? C.surface : C.encre }}>{valeur}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Mes classes (liste — /enseignant/mes-classes)              */
/* ------------------------------------------------------------------ */

function SectionClassesPersonnelles({ token }) {
  const [classesPerso, setClassesPerso] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [ouvert, setOuvert] = useState(false);
  const [nom, setNom] = useState("");
  const [matiereId, setMatiereId] = useState("");
  const [niveau, setNiveau] = useState("");
  const [effectif, setEffectif] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/enseignant/classes-personnelles", { token }).then(setClassesPerso).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);
  useEffect(() => {
    apiFetch("/enseignant/matieres", { token }).then((m) => { setMatieres(m); if (m[0]) setMatiereId(m[0].id); }).catch(() => {});
  }, [token]);

  async function creer(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null);
    try {
      await apiFetch("/enseignant/classes-personnelles", {
        method: "POST", token,
        body: { nom, matiere_id: matiereId, niveau, effectif: effectif ? Number(effectif) : null },
      });
      setNom(""); setNiveau(""); setEffectif(""); setOuvert(false);
      charger();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  async function supprimer(id) {
    try {
      await apiFetch(`/enseignant/classes-personnelles/${id}`, { method: "DELETE", token });
      setClassesPerso((prev) => prev.filter((c) => c.id !== id));
    } catch (e) { setErreur(e.message); }
  }

  return (
    <div className="mt-10">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="eduai-display text-xl" style={{ color: C.encre }}>Mes classes personnelles</h2>
          <p className="text-xs" style={{ color: C.encreAttenue }}>Déclarées par vous-même — pas d'élèves réels, juste un contexte pour générer vos cours.</p>
        </div>
      </div>

      <BandeauErreur message={erreur} />

      {ouvert ? (
        <form onSubmit={creer} className="rounded-lg p-4 border space-y-2.5 mb-4" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
          <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom (ex : Soutien Terminale D)"
            className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
          <div className="grid grid-cols-3 gap-2">
            <select value={matiereId} onChange={(e) => setMatiereId(e.target.value)} required
              className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
              {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom}</option>)}
            </select>
            <input required value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="Niveau (ex : Terminale D)"
              className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
            <input type="number" value={effectif} onChange={(e) => setEffectif(e.target.value)} placeholder="Effectif (optionnel)"
              className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
          </div>
          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={envoi} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
              {envoi ? <Loader2 size={12} className="eduai-spin" /> : "Créer"}
            </button>
            <button type="button" onClick={() => setOuvert(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
          </div>
        </form>
      ) : (
        <button onClick={() => setOuvert(true)} className="eduai-focus flex items-center gap-1.5 text-xs font-medium mb-4" style={{ color: C.accentFonce }}>
          <Plus size={13} /> Déclarer une classe personnelle
        </button>
      )}

      {chargement ? <Chargement /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {classesPerso.map((cl) => (
            <div key={cl.id} className="rounded-xl p-4 border flex items-start justify-between" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
              <div>
                <p className="text-xs font-medium mb-1" style={{ color: C.encreDoux }}>{cl.matiere} · {cl.niveau}</p>
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{cl.nom}</p>
                {cl.effectif != null && <p className="text-[11px] mt-1" style={{ color: C.encreAttenue }}>{cl.effectif} élève{cl.effectif > 1 ? "s" : ""}</p>}
              </div>
              <button onClick={() => supprimer(cl.id)} className="eduai-focus" aria-label="Supprimer" style={{ color: C.encreAttenue }}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {classesPerso.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucune classe personnelle déclarée pour l'instant.</p>}
        </div>
      )}
    </div>
  );
}

function EcranMesClasses({ classes, chargement, erreur, setVue, setClasseActive, token }) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Mes classes</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>{classes.length} classe{classes.length !== 1 ? "s" : ""} affectée{classes.length !== 1 ? "s" : ""}.</p>

      <BandeauErreur message={erreur} />
      {chargement ? <Chargement label="Chargement de vos classes..." /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {classes.map((cl) => {
            const { icon: Icon, papier } = infoMatiere(cl.matiere);
            return (
              <button
                key={`${cl.classe_id}-${cl.matiere_id}`}
                onClick={() => { setClasseActive(cl); setVue("classe-detail"); }}
                className={`eduai-focus text-left rounded-xl p-5 border eduai-paper-${papier} transition-transform hover:-translate-y-0.5`}
                style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `3px solid ${C.accent}` }}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon size={16} color={C.encre} />
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                    {cl.effectif} élève{cl.effectif !== 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-xs font-medium mb-1.5" style={{ color: C.encreDoux }}>{cl.matiere}</p>
                <p className="text-sm font-semibold mb-1" style={{ color: C.encre }}>{cl.nom}</p>
                <p className="text-[11px] mb-3" style={{ color: C.encreAttenue }}>{cl.etablissement_nom}</p>
                <div className="flex items-center gap-1.5 text-xs" style={{ color: C.accentFonce }}>
                  <TrendingUp size={12} /> Moyenne de classe : {cl.moyenne_classe === null ? "—" : `${cl.moyenne_classe}/20`}
                </div>
              </button>
            );
          })}
          {classes.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucune classe affectée pour l'instant.</p>}
        </div>
      )}

      {token && <SectionClassesPersonnelles token={token} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail d'une classe (élèves — GET .../classes/{id}/eleves) */
/* ------------------------------------------------------------------ */

function EcranClasseDetail({ classeActive, token, setVue, setEleveActif }) {
  const [eleves, setEleves] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    let annule = false;
    setChargement(true); setErreur(null);
    apiFetch(`/enseignant/classes/${classeActive.classe_id}/eleves`, { token, params: { matiere_id: classeActive.matiere_id } })
      .then((d) => { if (!annule) setEleves(d); })
      .catch((e) => { if (!annule) setErreur(e.message); })
      .finally(() => { if (!annule) setChargement(false); });
    return () => { annule = true; };
  }, [classeActive, token]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("mes-classes")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour à mes classes
      </button>

      <p className="text-xs font-medium mb-1" style={{ color: C.accentFonce }}>{classeActive.matiere}</p>
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>{classeActive.nom}</h1>

      <BandeauErreur message={erreur} />
      {chargement ? <Chargement label="Chargement des élèves..." /> : (
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          {eleves.map((el, i) => (
            <button
              key={el.eleve_id}
              onClick={() => { setEleveActif(el); setVue("eleve-detail"); }}
              className="eduai-focus w-full text-left px-5 py-4 flex items-center justify-between transition-colors"
              style={{ borderTop: i > 0 ? `1px solid ${C.ligne}` : "none" }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = C.fond)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              <div>
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{el.nom} {el.prenom}</p>
                <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{el.matricule || "—"}</p>
              </div>
              <div className="flex items-center gap-4">
                {el.nombre_absences > 0 && (
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                    <CalendarX size={10} /> {el.nombre_absences}
                  </span>
                )}
                <span className="eduai-mono text-sm font-semibold" style={{ color: el.moyenne === null ? C.encreAttenue : C.encre }}>
                  {el.moyenne === null ? "—" : `${el.moyenne}/20`}
                </span>
                <ChevronRight size={14} color={C.encreAttenue} />
              </div>
            </button>
          ))}
          {eleves.length === 0 && <p className="text-sm px-5 py-6" style={{ color: C.encreDoux }}>Aucun élève dans cette classe.</p>}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail d'un élève (notes + absences réelles)                */
/* ------------------------------------------------------------------ */

function EcranEleveDetail({ eleveActif, classeActive, token, setVue }) {
  const [onglet, setOnglet] = useState("notes");
  const [notes, setNotes] = useState([]);
  const [absences, setAbsences] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  const [formuleNote, setFormuleNote] = useState(false);
  const [valeur, setValeur] = useState("");
  const [bareme, setBareme] = useState("20");
  const [typeEval, setTypeEval] = useState("controle");
  const [trimestre, setTrimestre] = useState(1);
  const [envoiNote, setEnvoiNote] = useState(false);

  const [formuleAbsence, setFormuleAbsence] = useState(false);
  const [dateAbsence, setDateAbsence] = useState("");
  const [typeAbsence, setTypeAbsence] = useState("absence");
  const [justifie, setJustifie] = useState(false);
  const [motif, setMotif] = useState("");
  const [envoiAbsence, setEnvoiAbsence] = useState(false);

  const chargerDonnees = useCallback(() => {
    setChargement(true); setErreur(null);
    Promise.all([
      apiFetch(`/enseignant/eleves/${eleveActif.eleve_id}/notes`, { token, params: { matiere_id: classeActive.matiere_id } }),
      apiFetch(`/enseignant/eleves/${eleveActif.eleve_id}/absences`, { token, params: { matiere_id: classeActive.matiere_id } }),
    ])
      .then(([n, a]) => { setNotes(n); setAbsences(a); })
      .catch((e) => setErreur(e.message))
      .finally(() => setChargement(false));
  }, [eleveActif, classeActive, token]);

  useEffect(() => { chargerDonnees(); }, [chargerDonnees]);

  const moyenne = notes.length
    ? notes.reduce((s, n) => s + (n.valeur / n.bareme) * 20, 0) / notes.length
    : null;

  async function soumettreNote(e) {
    e.preventDefault();
    setEnvoiNote(true); setErreur(null);
    try {
      const nouvelle = await apiFetch(`/enseignant/eleves/${eleveActif.eleve_id}/notes`, {
        method: "POST", token,
        body: { matiere_id: classeActive.matiere_id, valeur: parseFloat(valeur), bareme: parseFloat(bareme), type_evaluation: typeEval, trimestre },
      });
      setNotes((prev) => [nouvelle, ...prev]);
      setValeur(""); setFormuleNote(false);
    } catch (e) { setErreur(e.message); }
    finally { setEnvoiNote(false); }
  }

  async function soumettreAbsence(e) {
    e.preventDefault();
    setEnvoiAbsence(true); setErreur(null);
    try {
      const nouvelle = await apiFetch(`/enseignant/eleves/${eleveActif.eleve_id}/absences`, {
        method: "POST", token, params: { matiere_id: classeActive.matiere_id },
        body: { date_absence: dateAbsence, type_absence: typeAbsence, justifie, motif: motif || null },
      });
      setAbsences((prev) => [nouvelle, ...prev]);
      setDateAbsence(""); setMotif(""); setJustifie(false); setFormuleAbsence(false);
    } catch (e) { setErreur(e.message); }
    finally { setEnvoiAbsence(false); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("classe-detail")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour à {classeActive.nom}
      </button>

      <p className="text-xs font-medium mb-1" style={{ color: C.accentFonce }}>{classeActive.nom} · {eleveActif.matricule || "—"}</p>
      <h1 className="eduai-display text-3xl mb-1" style={{ color: C.encre }}>{eleveActif.nom} {eleveActif.prenom}</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        Moyenne en {classeActive.matiere} : <span className="eduai-mono font-semibold" style={{ color: C.encre }}>{moyenne === null ? "—" : `${moyenne.toFixed(1)}/20`}</span>
      </p>

      <BandeauErreur message={erreur} />

      <div className="flex gap-2 mb-6">
        <ChipMatiere label="Notes" active={onglet === "notes"} onClick={() => setOnglet("notes")} />
        <ChipMatiere label="Absences" active={onglet === "absences"} onClick={() => setOnglet("absences")} />
      </div>

      {chargement ? <Chargement /> : onglet === "notes" ? (
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium" style={{ color: C.encreDoux }}>{notes.length} note{notes.length !== 1 ? "s" : ""}</span>
            {!formuleNote && (
              <button onClick={() => setFormuleNote(true)} className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.accentFonce }}>
                <Plus size={12} /> Ajouter une note
              </button>
            )}
          </div>

          {formuleNote && (
            <form onSubmit={soumettreNote} className="rounded-xl p-5 border mb-4 space-y-3" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Note</span>
                  <input required type="number" step="0.5" min="0" value={valeur} onChange={(e) => setValeur(e.target.value)}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
                </label>
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Barème</span>
                  <input required type="number" value={bareme} onChange={(e) => setBareme(e.target.value)}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Type</span>
                  <select value={typeEval} onChange={(e) => setTypeEval(e.target.value)}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
                    {TYPES_EVALUATION.map((t) => <option key={t} value={t}>{TYPE_EVALUATION_LABEL[t]}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Trimestre</span>
                  <select value={trimestre} onChange={(e) => setTrimestre(parseInt(e.target.value))}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
                    {TRIMESTRES.map((t) => <option key={t} value={t}>Trimestre {t}</option>)}
                  </select>
                </label>
              </div>
              <div className="flex gap-2 pt-1">
                <button type="submit" disabled={envoiNote} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                  {envoiNote && <Loader2 size={12} className="eduai-spin" />} Enregistrer
                </button>
                <button type="button" onClick={() => setFormuleNote(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
              </div>
            </form>
          )}

          <div className="space-y-2.5">
            {notes.map((n) => (
              <div key={n.id} className="rounded-xl px-5 py-3.5 flex items-center justify-between border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
                <div>
                  <p className="text-sm font-medium" style={{ color: C.encre }}>{TYPE_EVALUATION_LABEL[n.type_evaluation]}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>Trimestre {n.trimestre}</p>
                </div>
                <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>{n.valeur}/{n.bareme}</span>
              </div>
            ))}
            {notes.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucune note enregistrée.</p>}
          </div>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium" style={{ color: C.encreDoux }}>{absences.length} entrée{absences.length !== 1 ? "s" : ""}</span>
            {!formuleAbsence && (
              <button onClick={() => setFormuleAbsence(true)} className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.accentFonce }}>
                <Plus size={12} /> Signaler
              </button>
            )}
          </div>

          {formuleAbsence && (
            <form onSubmit={soumettreAbsence} className="rounded-xl p-5 border mb-4 space-y-3" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Date</span>
                  <input required type="date" value={dateAbsence} onChange={(e) => setDateAbsence(e.target.value)}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
                </label>
                <label className="block">
                  <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Type</span>
                  <select value={typeAbsence} onChange={(e) => setTypeAbsence(e.target.value)}
                    className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                    style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
                    <option value="absence">Absence</option>
                    <option value="retard">Retard</option>
                  </select>
                </label>
              </div>
              <label className="flex items-center gap-2 text-xs" style={{ color: C.encreDoux }}>
                <input type="checkbox" checked={justifie} onChange={(e) => setJustifie(e.target.checked)} />
                Justifié
              </label>
              <label className="block">
                <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Motif (optionnel)</span>
                <input value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Ex : certificat médical"
                  className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border"
                  style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
              </label>
              <div className="flex gap-2 pt-1">
                <button type="submit" disabled={envoiAbsence} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                  {envoiAbsence && <Loader2 size={12} className="eduai-spin" />} Enregistrer
                </button>
                <button type="button" onClick={() => setFormuleAbsence(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
              </div>
            </form>
          )}

          <div className="space-y-2.5">
            {absences.map((a) => (
              <div key={a.id} className="rounded-xl px-5 py-3.5 flex items-center justify-between border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
                <div>
                  <p className="text-sm font-medium" style={{ color: C.encre }}>{a.type_absence === "absence" ? "Absence" : "Retard"} — {a.date_absence}</p>
                  {a.motif && <p className="text-xs mt-0.5 italic" style={{ color: C.encreAttenue }}>« {a.motif} »</p>}
                </div>
                <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: a.justifie ? C.vertFond : C.rougeFond, color: a.justifie ? C.vert : C.rouge }}>
                  {a.justifie ? "Justifié" : "Non justifié"}
                </span>
              </div>
            ))}
            {absences.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucune absence enregistrée.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Mes cours                                                   */
/* ------------------------------------------------------------------ */

function EcranMesCours({ cours, chargement, erreur, setVue, setCoursActifId, classes }) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="eduai-display text-3xl mb-1" style={{ color: C.encre }}>Mes cours</h1>
          <p className="text-sm" style={{ color: C.encreDoux }}>{cours.length} cours déposés dans ta banque personnelle.</p>
        </div>
        <button onClick={() => setVue("deposer-cours")} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>
          <Plus size={15} /> Déposer un cours
        </button>
      </div>

      <BandeauErreur message={erreur} />
      {chargement ? <Chargement label="Chargement de vos cours..." /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {cours.map((c) => {
            const { icon: Icon, papier } = infoMatiere(c.matiere);
            return (
              <button
                key={c.id}
                onClick={() => { setCoursActifId(c.id); setVue("cours-detail"); }}
                className={`eduai-focus text-left rounded-xl p-5 border eduai-paper-${papier} transition-transform hover:-translate-y-0.5`}
                style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `3px solid ${C.accent}` }}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon size={16} color={C.encre} />
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.vertFond, color: C.vert }}>
                    {c.nombre_ressources_validees}/{c.nombre_ressources_total} validées
                  </span>
                </div>
                <p className="text-xs font-medium mb-1.5" style={{ color: C.encreDoux }}>{c.matiere} · {c.classe}</p>
                <p className="text-sm font-semibold leading-snug" style={{ color: C.encre }}>{c.titre}</p>
              </button>
            );
          })}
          {cours.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun cours déposé pour l'instant.</p>}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Déposer un cours (classe/matière limitées aux affectations)*/
/* ------------------------------------------------------------------ */

function EcranDeposerCours({ classes, token, setVue, onCoursDepose }) {
  const [classesPerso, setClassesPerso] = useState([]);
  const [chargementPerso, setChargementPerso] = useState(true);

  useEffect(() => {
    apiFetch("/enseignant/classes-personnelles", { token }).then(setClassesPerso).catch(() => {}).finally(() => setChargementPerso(false));
  }, [token]);

  const options = [
    ...classes.map((cl) => ({ valeur: `etab:${cl.classe_id}:${cl.matiere_id}`, label: `${cl.nom} — ${cl.matiere} (${cl.etablissement_nom})` })),
    ...classesPerso.map((cl) => ({ valeur: `perso:${cl.id}:${cl.matiere_id}`, label: `${cl.nom} — ${cl.matiere} (personnelle)` })),
  ];

  const [choix, setChoix] = useState("");
  useEffect(() => { if (!choix && options.length) setChoix(options[0].valeur); }, [options.length]);

  const [titre, setTitre] = useState("");
  const [contenu, setContenu] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const [type, id, matiere_id] = choix.split(":");
    setEnvoi(true); setErreur(null);
    try {
      const body = { titre, matiere_id, contenu_texte: contenu || null };
      if (type === "etab") body.classe_id = id; else body.classe_personnelle_id = id;
      const cours = await apiFetch("/enseignant/cours", { method: "POST", token, body });
      onCoursDepose(cours);
      setVue("cours-detail");
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  if (chargementPerso) return <Chargement />;

  if (options.length === 0) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
        <BandeauErreur message="Aucune classe disponible pour l'instant." />
        <p className="text-sm mb-4" style={{ color: C.encreDoux }}>
          Vous n'êtes affecté à aucune classe d'établissement, et vous n'avez pas encore déclaré de classe personnelle.
        </p>
        <button onClick={() => setVue("mes-classes")} className="eduai-focus rounded-lg px-4 py-2.5 text-sm font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>
          Déclarer une classe personnelle
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("mes-cours")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour à mes cours
      </button>

      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Déposer un cours</h1>
      <p className="text-sm mb-2" style={{ color: C.encreDoux }}>
        L'IA génère automatiquement une fiche pédagogique, un résumé, des exercices, un QCM, un devoir et un contrôle.
      </p>
      <p className="flex items-center gap-1.5 text-xs mb-8" style={{ color: C.encreAttenue }}>
        <AlertTriangle size={11} /> EduAI peut faire des erreurs, toujours vérifier les informations et surtout valider les exercices avant de les mettre à la disposition des élèves.
      </p>

      <BandeauErreur message={erreur} />

      <form onSubmit={handleSubmit} className="rounded-2xl p-7 border space-y-5" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <label className="block">
          <span className="text-xs font-medium mb-1.5 block" style={{ color: C.encreDoux }}>Titre du cours</span>
          <input required value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Ex : Les nombres décimaux"
            className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
            style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
        </label>

        <label className="block">
          <span className="text-xs font-medium mb-1.5 block" style={{ color: C.encreDoux }}>Classe / matière</span>
          <select value={choix} onChange={(e) => setChoix(e.target.value)}
            className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
            style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
            {options.map((o) => <option key={o.valeur} value={o.valeur}>{o.label}</option>)}
          </select>
          <span className="text-[11px] mt-1 block" style={{ color: C.encreAttenue }}>
            Limité à vos affectations réelles.
          </span>
        </label>

        <label className="block">
          <span className="text-xs font-medium mb-1.5 block" style={{ color: C.encreDoux }}>Contenu du cours</span>
          <textarea value={contenu} onChange={(e) => setContenu(e.target.value)} rows={5}
            placeholder="Colle ou saisis le contenu de ton cours ici..."
            className="eduai-focus eduai-textarea w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border"
            style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
        </label>

        <button
          type="submit" disabled={envoi}
          className="eduai-focus w-full flex items-center justify-center gap-2 rounded-lg py-3 text-sm font-semibold transition-colors disabled:opacity-60"
          style={{ backgroundColor: C.encre, color: C.surface }}
        >
          {envoi ? <Loader2 size={15} className="eduai-spin" /> : <Sparkles size={15} />}
          {envoi ? "Génération en cours..." : "Déposer et générer les ressources"}
        </button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail d'un cours + ressources (GET/PATCH réels)           */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Rendu structuré des ressources — une présentation par type,        */
/*  plutôt qu'un simple bloc de texte (voir generation_cours.py)       */
/* ------------------------------------------------------------------ */

// Convertit n'importe quelle structure en texte lisible — utilisé
// uniquement pour préremplir la zone d'édition (miroir de la fonction
// Python _aplatir_en_texte). Une fois modifié et enregistré, le contenu
// redevient un simple texte (perd la mise en forme dédiée), ce qui reste
// un compromis raisonnable pour ne pas construire un éditeur par type.
function aplatirPourEdition(valeur, niveau = 0) {
  const prefixe = "  ".repeat(niveau);
  if (typeof valeur === "string") return valeur;
  if (valeur === null || valeur === undefined) return "";
  if (typeof valeur === "number" || typeof valeur === "boolean") return String(valeur);
  if (Array.isArray(valeur)) return valeur.map((v) => `${prefixe}- ${aplatirPourEdition(v, niveau + 1)}`).join("\n");
  if (typeof valeur === "object") {
    return Object.entries(valeur).map(([cle, sousValeur]) => {
      const libelle = cle.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
      const sousTexte = aplatirPourEdition(sousValeur, niveau + 1);
      return sousTexte.includes("\n") ? `${prefixe}${libelle} :\n${sousTexte}` : `${prefixe}${libelle} : ${sousTexte}`;
    }).join("\n");
  }
  return String(valeur);
}

function BlocExercice({ numero, difficulte, points, enonce, corrige }) {
  const [ouvert, setOuvert] = useState(false);
  return (
    <div className="rounded-lg border px-3.5 py-3" style={{ borderColor: C.ligne }}>
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="eduai-mono text-xs font-semibold" style={{ color: C.accentFonce }}>Exercice {numero}</span>
        {difficulte && (
          <span className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={badgeColorForDifficulte(difficulte)}>{difficulte}</span>
        )}
        {points != null && (
          <span className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ backgroundColor: C.bleuFond, color: C.encre }}>{points} pts</span>
        )}
      </div>
      <p className="text-sm mb-2 whitespace-pre-wrap" style={{ color: C.encre }}>{enonce}</p>
      <button onClick={() => setOuvert((o) => !o)} className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.accentFonce }}>
        <ChevronDown size={12} style={{ transform: ouvert ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />
        {ouvert ? "Masquer le corrigé" : "Voir le corrigé"}
      </button>
      {ouvert && <p className="text-sm mt-2 pt-2 border-t whitespace-pre-wrap" style={{ borderColor: C.ligne, color: C.encreDoux }}>{corrige}</p>}
    </div>
  );
}

function RenduFichePedagogique({ contenu }) {
  return (
    <div className="space-y-4">
      {contenu.objectifs?.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5" style={{ color: C.encre }}>Objectifs</p>
          <ul className="list-disc list-inside text-sm space-y-0.5" style={{ color: C.encreDoux }}>
            {contenu.objectifs.map((o, i) => <li key={i}>{o}</li>)}
          </ul>
        </div>
      )}
      {contenu.competences_visees?.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5" style={{ color: C.encre }}>Compétences visées</p>
          <ul className="list-disc list-inside text-sm space-y-0.5" style={{ color: C.encreDoux }}>
            {contenu.competences_visees.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}
      {contenu.deroulement?.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5" style={{ color: C.encre }}>Déroulement</p>
          <div className="space-y-2">
            {contenu.deroulement.map((etape, i) => (
              <div key={i} className="rounded-lg border px-3 py-2" style={{ borderColor: C.ligne }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold" style={{ color: C.encre }}>{etape.etape}</span>
                  {etape.duree && (
                    <span className="flex items-center gap-1 text-[10px] rounded-full px-2 py-0.5" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                      <Clock size={9} /> {etape.duree}
                    </span>
                  )}
                </div>
                <p className="text-sm" style={{ color: C.encreDoux }}>{etape.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RenduResume({ contenu }) {
  return (
    <div className="space-y-4">
      {contenu.definitions_cles?.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5" style={{ color: C.encre }}>Définitions clés</p>
          <div className="space-y-1.5">
            {contenu.definitions_cles.map((d, i) => (
              <p key={i} className="text-sm" style={{ color: C.encreDoux }}>
                <span className="font-semibold" style={{ color: C.encre }}>{d.terme}</span> — {d.definition}
              </p>
            ))}
          </div>
        </div>
      )}
      {contenu.regles_principales?.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5" style={{ color: C.encre }}>Règles principales</p>
          <ul className="list-disc list-inside text-sm space-y-0.5" style={{ color: C.encreDoux }}>
            {contenu.regles_principales.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
      {contenu.exemple_travaille && (
        <div className="rounded-lg px-3 py-2.5" style={{ backgroundColor: C.fond }}>
          <p className="text-xs font-semibold mb-1" style={{ color: C.encre }}>Exemple travaillé</p>
          <p className="text-sm mb-1.5 whitespace-pre-wrap" style={{ color: C.encre }}>{contenu.exemple_travaille.enonce}</p>
          <p className="text-sm whitespace-pre-wrap" style={{ color: C.encreDoux }}>{contenu.exemple_travaille.resolution}</p>
        </div>
      )}
    </div>
  );
}

function RenduExercices({ contenu }) {
  return (
    <div className="space-y-2.5">
      {(contenu.exercices || []).map((ex, i) => (
        <BlocExercice key={i} numero={ex.numero ?? i + 1} difficulte={ex.difficulte} points={ex.points} enonce={ex.enonce} corrige={ex.corrige} />
      ))}
    </div>
  );
}

function RenduQcm({ contenu }) {
  return (
    <div className="space-y-3">
      {(contenu.questions || []).map((q, i) => (
        <div key={i} className="rounded-lg border px-3.5 py-3" style={{ borderColor: C.ligne }}>
          <p className="text-sm font-medium mb-2" style={{ color: C.encre }}>{q.numero ?? i + 1}. {q.question}</p>
          <div className="space-y-1">
            {(q.choix || []).map((choix, j) => {
              const estBonne = j === q.bonne_reponse;
              return (
                <div key={j} className="flex items-center gap-2 text-sm rounded-md px-2 py-1"
                  style={estBonne ? { backgroundColor: C.vertFond, color: C.vert } : { color: C.encreDoux }}>
                  {estBonne ? <Check size={13} /> : <span className="w-[13px] text-center eduai-mono text-[10px]">{String.fromCharCode(65 + j)}</span>}
                  <span>{choix}</span>
                </div>
              );
            })}
          </div>
          {q.explication && <p className="text-xs mt-2 italic" style={{ color: C.encreAttenue }}>{q.explication}</p>}
        </div>
      ))}
    </div>
  );
}

function RenduDevoirOuControle({ contenu, cleFinale, labelFinal }) {
  const blocFinal = contenu[cleFinale];
  return (
    <div className="space-y-2.5">
      {contenu.duree && (
        <p className="flex items-center gap-1 text-xs" style={{ color: C.encreAttenue }}><Clock size={11} /> {contenu.duree}</p>
      )}
      {(contenu.exercices || []).map((ex, i) => (
        <BlocExercice key={i} numero={ex.numero ?? i + 1} points={ex.points} enonce={ex.enonce} corrige={ex.corrige} />
      ))}
      {blocFinal && (
        <div className="rounded-lg border-2 px-3.5 py-3" style={{ borderColor: C.accent }}>
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles size={13} color={C.accentFonce} />
            <span className="text-xs font-semibold" style={{ color: C.accentFonce }}>{labelFinal}</span>
            {blocFinal.points != null && (
              <span className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ backgroundColor: C.bleuFond, color: C.encre }}>{blocFinal.points} pts</span>
            )}
          </div>
          <BlocExercice numero="" difficulte={null} points={null} enonce={blocFinal.enonce} corrige={blocFinal.corrige} />
        </div>
      )}
    </div>
  );
}

function RenduRessource({ type, contenu }) {
  if (!contenu) return null;
  // Repli : l'IA n'a pas respecté le schéma attendu, ou la ressource a été
  // modifiée manuellement — on affiche simplement le texte.
  if (contenu.texte !== undefined && Object.keys(contenu).length === 1) {
    return <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: C.encreDoux }}>{contenu.texte}</p>;
  }

  // Filet de sécurité supplémentaire côté frontend : même si le backend a
  // validé la structure, on vérifie que le rendu dédié aurait bien
  // quelque chose à montrer avant de s'y engager — sinon on affiche le
  // contenu aplati plutôt qu'une carte vide (incident du 03/08).
  const estListeNonVide = (v) => Array.isArray(v) && v.length > 0;
  const structureAffichable = {
    fiche_pedagogique: estListeNonVide(contenu.objectifs) && estListeNonVide(contenu.deroulement),
    resume: estListeNonVide(contenu.definitions_cles) && estListeNonVide(contenu.regles_principales),
    exercices: estListeNonVide(contenu.exercices),
    qcm: estListeNonVide(contenu.questions),
    devoir: estListeNonVide(contenu.exercices) && !!contenu.probleme,
    controle: estListeNonVide(contenu.exercices) && !!contenu.exercice_synthese,
  }[type];

  if (!structureAffichable) {
    return <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: C.encreDoux }}>{aplatirPourEdition(contenu)}</p>;
  }

  switch (type) {
    case "fiche_pedagogique": return <RenduFichePedagogique contenu={contenu} />;
    case "resume": return <RenduResume contenu={contenu} />;
    case "exercices": return <RenduExercices contenu={contenu} />;
    case "qcm": return <RenduQcm contenu={contenu} />;
    case "devoir": return <RenduDevoirOuControle contenu={contenu} cleFinale="probleme" labelFinal="Problème" />;
    case "controle": return <RenduDevoirOuControle contenu={contenu} cleFinale="exercice_synthese" labelFinal="Exercice de synthèse" />;
    default: return <p className="text-sm whitespace-pre-wrap" style={{ color: C.encreDoux }}>{contenu.texte || aplatirPourEdition(contenu)}</p>;
  }
}

function EcranCoursDetail({ coursId, token, setVue }) {
  const [cours, setCours] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [editionId, setEditionId] = useState(null);
  const [brouillon, setBrouillon] = useState("");
  const [enregistrement, setEnregistrement] = useState(false);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/enseignant/cours/${coursId}`, { token })
      .then(setCours)
      .catch((e) => setErreur(e.message))
      .finally(() => setChargement(false));
  }, [coursId, token]);

  useEffect(() => { charger(); }, [charger]);

  async function majRessource(ressourceId, changements) {
    setEnregistrement(true); setErreur(null);
    try {
      await apiFetch(`/enseignant/cours/${coursId}/ressources/${ressourceId}`, { method: "PATCH", token, body: changements });
      await charger();
      setEditionId(null);
    } catch (e) { setErreur(e.message); }
    finally { setEnregistrement(false); }
  }

  if (chargement) return <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10"><Chargement label="Chargement du cours..." /></div>;
  if (erreur && !cours) return <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10"><BandeauErreur message={erreur} /></div>;
  if (!cours) return null;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("mes-cours")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour à mes cours
      </button>

      <p className="text-xs font-medium mb-1" style={{ color: C.accentFonce }}>{cours.matiere} · {cours.classe}</p>
      <h1 className="eduai-display text-2xl mb-8" style={{ color: C.encre }}>{cours.titre}</h1>

      <BandeauErreur message={erreur} />

      <div className="space-y-4">
        {cours.ressources.map((r) => {
          const meta = TYPES_RESSOURCE.find((t) => t.key === r.type_ressource) || TYPES_RESSOURCE[0];
          const Icon = meta.icon;
          const enEdition = editionId === r.id;
          return (
            <div key={r.id} className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2">
                  <Icon size={15} color={C.accentFonce} />
                  <span className="text-sm font-semibold" style={{ color: C.encre }}>{r.label || meta.label}</span>
                </div>
                {r.statut === "valide" && (
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: C.vertFond, color: C.vert }}><Check size={10} /> Validée</span>
                )}
                {r.statut === "corrige" && (
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.bleuFond, color: C.encre }}>Modifiée</span>
                )}
                {r.statut === "en_attente" && (
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.ambreFond, color: C.ambre }}>À relire</span>
                )}
              </div>

              {enEdition ? (
                <>
                  <textarea value={brouillon} onChange={(e) => setBrouillon(e.target.value)} rows={8}
                    className="eduai-focus eduai-textarea w-full rounded-lg px-3.5 py-2.5 text-sm border mb-3"
                    style={{ borderColor: C.accent, backgroundColor: C.fond, color: C.encre }} />
                  <div className="flex gap-2">
                    <button
                      onClick={() => majRessource(r.id, { contenu: { texte: brouillon }, statut: "corrige" })}
                      disabled={enregistrement}
                      className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60"
                      style={{ backgroundColor: C.encre, color: C.surface }}
                    >
                      Enregistrer
                    </button>
                    <button onClick={() => setEditionId(null)} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
                  </div>
                  <p className="text-[11px] mt-2" style={{ color: C.encreAttenue }}>
                    La modification remplace la mise en forme dédiée par un texte simple.
                  </p>
                </>
              ) : (
                <>
                  <div className="mb-3"><RenduRessource type={r.type_ressource} contenu={r.contenu} /></div>
                  <div className="flex gap-2">
                    {r.statut !== "valide" && (
                      <button onClick={() => majRessource(r.id, { statut: "valide" })} disabled={enregistrement}
                        className="eduai-focus flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-60"
                        style={{ backgroundColor: C.vertFond, color: C.vert }}>
                        <Check size={12} /> Valider
                      </button>
                    )}
                    <button onClick={() => { setEditionId(r.id); setBrouillon(r.contenu?.texte || aplatirPourEdition(r.contenu)); }}
                      className="eduai-focus flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                      <Pencil size={12} /> Modifier
                    </button>
                    <button onClick={() => majRessource(r.id, { statut: "supprime" })} disabled={enregistrement}
                      className="eduai-focus flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-60"
                      style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                      <Trash2 size={12} /> Supprimer
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : File de validation (exercices — API réelle)                */
/* ------------------------------------------------------------------ */

function EcranFile({ enAttente, chargement, erreur, setExerciceActifId, setVue, filtre, setFiltre }) {
  const filtres = filtre ? enAttente.filter((e) => e.matiere === filtre) : enAttente;
  const matieresPresentes = [...new Set(enAttente.map((e) => e.matiere))];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>File de validation</h1>
      <p className="text-sm mb-6" style={{ color: C.encreDoux }}>
        {enAttente.length} exercice{enAttente.length !== 1 ? "s" : ""} de la bibliothèque commune en attente dans ton périmètre.
      </p>

      <BandeauErreur message={erreur} />

      <div className="flex gap-2 mb-8 overflow-x-auto pb-1">
        <ChipMatiere label="Toutes" active={!filtre} onClick={() => setFiltre(null)} />
        {matieresPresentes.map((m) => {
          const { icon } = infoMatiere(m);
          return <ChipMatiere key={m} label={m} active={filtre === m} onClick={() => setFiltre(m)} icon={icon} />;
        })}
      </div>

      {chargement ? <Chargement label="Chargement de la file..." /> : filtres.length === 0 ? (
        <div className="rounded-xl p-8 text-center border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
          <p className="text-sm" style={{ color: C.encreDoux }}>Rien à relire ici pour le moment.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {filtres.map((ex) => {
            const { icon: Icon, papier } = infoMatiere(ex.matiere);
            const badgeDiff = badgeColorForDifficulte(ex.difficulte);
            const badgeSrc = badgeSource(ex.source);
            return (
              <button
                key={ex.id}
                onClick={() => { setExerciceActifId(ex.id); setVue("exercice-detail"); }}
                className={`eduai-focus text-left rounded-xl p-5 border eduai-paper-${papier} transition-transform hover:-translate-y-0.5`}
                style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `3px solid ${C.accent}` }}
              >
                <div className="flex items-start justify-between mb-3 gap-2">
                  <Icon size={16} color={C.encre} />
                  <div className="flex gap-1.5 flex-wrap justify-end">
                    <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap" style={{ backgroundColor: badgeDiff.bg, color: badgeDiff.fg }}>
                      {DIFFICULTE_LABEL[ex.difficulte]}
                    </span>
                    <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap flex items-center gap-1" style={{ backgroundColor: badgeSrc.bg, color: badgeSrc.fg }}>
                      <badgeSrc.Icon size={10} /> {badgeSrc.label}
                    </span>
                  </div>
                </div>
                <p className="text-xs font-medium mb-1.5" style={{ color: C.encreDoux }}>{ex.matiere} · {ex.niveau} · {ex.theme}</p>
                <p className="text-sm leading-snug" style={{ color: C.encre }}>{ex.enonce}</p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail / relecture d'un exercice (API réelle)              */
/* ------------------------------------------------------------------ */

function EcranExerciceDetail({ exerciceId, enAttente, token, setVue, onValider, onRejeter }) {
  const ex = enAttente.find((e) => e.id === exerciceId);
  const [enEdition, setEnEdition] = useState(false);
  const [enonce, setEnonce] = useState(ex?.enonce || "");
  const [corrige, setCorrige] = useState(ex?.corrige || "");
  const [modalRejet, setModalRejet] = useState(false);
  const [motif, setMotif] = useState("");
  const [motifErreur, setMotifErreur] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState(null);

  if (!ex) return null;
  const { papier } = infoMatiere(ex.matiere);
  const badgeDiff = badgeColorForDifficulte(ex.difficulte);
  const badgeSrc = badgeSource(ex.source);

  async function enregistrerModifications() {
    setEnCours(true); setErreur(null);
    try {
      await apiFetch(`/enseignant/exercices/${ex.id}`, { method: "PATCH", token, body: { enonce, corrige } });
      setEnEdition(false);
    } catch (e) { setErreur(e.message); }
    finally { setEnCours(false); }
  }

  async function valider() {
    setEnCours(true); setErreur(null);
    try { await onValider(ex.id); setVue("file"); }
    catch (e) { setErreur(e.message); }
    finally { setEnCours(false); }
  }

  async function confirmerRejet() {
    if (motif.trim().length < 5) { setMotifErreur(true); return; }
    setEnCours(true); setErreur(null);
    try { await onRejeter(ex.id, motif.trim()); setVue("file"); }
    catch (e) { setErreur(e.message); }
    finally { setEnCours(false); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("file")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour à la file
      </button>

      <BandeauErreur message={erreur} />

      <div className={`rounded-2xl p-7 border eduai-paper-${papier}`} style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `4px solid ${C.accent}` }}>
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs font-semibold" style={{ color: C.accentFonce }}>{ex.matiere}</span>
          <span style={{ color: C.ligne }}>·</span>
          <span className="text-xs" style={{ color: C.encreDoux }}>{ex.niveau} · {ex.theme}</span>
          <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full ml-auto flex items-center gap-1" style={{ backgroundColor: badgeSrc.bg, color: badgeSrc.fg }}>
            <badgeSrc.Icon size={10} /> {badgeSrc.label}
          </span>
          <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: badgeDiff.bg, color: badgeDiff.fg }}>{DIFFICULTE_LABEL[ex.difficulte]}</span>
        </div>

        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium" style={{ color: C.encreDoux }}>Énoncé</span>
          {!enEdition && (
            <button onClick={() => setEnEdition(true)} className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.accentFonce }}>
              <Pencil size={12} /> Corriger avant validation
            </button>
          )}
        </div>

        {enEdition ? (
          <textarea value={enonce} onChange={(e) => setEnonce(e.target.value)} rows={3}
            className="eduai-focus eduai-textarea w-full rounded-lg px-3.5 py-2.5 text-sm border mb-4 eduai-display"
            style={{ borderColor: C.accent, backgroundColor: C.fond, color: C.encre }} />
        ) : (
          <p className="eduai-display text-lg leading-relaxed mb-6" style={{ color: C.encre }}>{enonce}</p>
        )}

        <div className="rounded-xl p-5 mb-5" style={{ backgroundColor: C.fond, border: `1.5px dashed ${C.rouge}` }}>
          <span className="eduai-mono text-[10px] font-bold" style={{ color: C.rouge }}>CORRIGÉ</span>
          {enEdition ? (
            <textarea value={corrige} onChange={(e) => setCorrige(e.target.value)} rows={2}
              className="eduai-focus eduai-textarea w-full rounded-lg px-3.5 py-2.5 text-sm border mt-2"
              style={{ borderColor: C.accent, backgroundColor: C.surface, color: C.rouge }} />
          ) : (
            <p className="text-base font-semibold mt-1.5 mb-3" style={{ color: C.rouge }}>{corrige}</p>
          )}
          <ol className="space-y-1.5 mt-3">
            {(ex.etapes || []).map((etape, i) => (
              <li key={i} className="text-sm flex gap-2" style={{ color: C.encreDoux }}>
                <span className="eduai-mono" style={{ color: C.accentClair }}>{i + 1}.</span>{etape}
              </li>
            ))}
          </ol>
        </div>

        {enEdition && (
          <div className="flex gap-2 mb-5">
            <button onClick={enregistrerModifications} disabled={enCours} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
              Enregistrer les modifications
            </button>
            <button onClick={() => setEnEdition(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
          </div>
        )}

        <div className="flex gap-2.5">
          <button onClick={valider} disabled={enCours} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-60" style={{ backgroundColor: C.vert, color: C.surface }}>
            {enCours ? <Loader2 size={15} className="eduai-spin" /> : <Check size={15} />} Valider
          </button>
          <button onClick={() => setModalRejet(true)} disabled={enCours} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-60" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
            <XIcon size={15} /> Rejeter
          </button>
        </div>
      </div>

      {modalRejet && (
        <div className="fixed inset-0 z-20 flex items-center justify-center px-6" style={{ backgroundColor: "rgba(34,48,74,0.45)" }}>
          <div className="w-full max-w-sm rounded-2xl p-6 eduai-fade-in" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
            <h3 className="eduai-display text-lg mb-2" style={{ color: C.encre }}>Motif du rejet</h3>
            <p className="text-xs mb-4" style={{ color: C.encreDoux }}>Obligatoire — ça aide à ajuster les templates ou les prompts du pipeline.</p>
            <textarea value={motif} onChange={(e) => { setMotif(e.target.value); setMotifErreur(false); }} rows={3}
              placeholder="Ex : contexte peu clair pour ce niveau, à reformuler."
              className="eduai-focus eduai-textarea w-full rounded-lg px-3.5 py-2.5 text-sm border mb-1"
              style={{ borderColor: motifErreur ? C.rouge : C.ligne, backgroundColor: C.fond, color: C.encre }} />
            {motifErreur && <p className="text-xs mb-3" style={{ color: C.rouge }}>Merci de préciser un motif (5 caractères minimum).</p>}
            <div className="flex gap-2.5 mt-4">
              <button onClick={confirmerRejet} disabled={enCours} className="eduai-focus flex-1 rounded-lg py-2.5 text-sm font-semibold disabled:opacity-60" style={{ backgroundColor: C.rouge, color: C.surface }}>
                Confirmer le rejet
              </button>
              <button onClick={() => { setModalRejet(false); setMotif(""); setMotifErreur(false); }} className="eduai-focus rounded-lg px-4 py-2.5 text-sm font-medium" style={{ backgroundColor: C.fond, color: C.encreDoux }}>
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Historique (accumulé côté client — voir note en bas)       */
/* ------------------------------------------------------------------ */

function EcranHistorique({ token }) {
  const [historique, setHistorique] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true);
    apiFetch("/enseignant/exercices/mon-historique", { token })
      .then(setHistorique).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2 flex items-center gap-2" style={{ color: C.encre }}>
        <History size={24} /> Historique de validation
      </h1>
      <p className="text-xs mb-8" style={{ color: C.encreAttenue }}>
        Vos décisions sur la bibliothèque commune ("À valider"), quelle que soit la session. Les exercices générés
        via "Génération libre" ont leur propre historique, visible directement sur cette page-là.
      </p>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : historique.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucune décision enregistrée pour l'instant.</p>
      ) : (
        <div className="space-y-3">
          {historique.map((h) => (
            <div key={h.id} className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{h.theme}</p>
                <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: h.statut === "valide" ? C.vertFond : C.rougeFond, color: h.statut === "valide" ? C.vert : C.rouge }}>
                  {h.statut === "valide" ? <Check size={10} /> : <XIcon size={10} />}
                  {h.statut === "valide" ? "Validé" : "Rejeté"}
                </span>
              </div>
              <p className="text-xs mb-1" style={{ color: C.encreDoux }}>{h.matiere} · {h.niveau}</p>
              {h.motif && <p className="text-xs mt-2 italic" style={{ color: C.encreAttenue }}>« {h.motif} »</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Mes documents (notes de cours privées + partage)           */
/* ------------------------------------------------------------------ */

function BadgeStatutDocument({ statut }) {
  const map = {
    en_traitement: { label: "Indexation en cours...", bg: C.bleuFond, fg: C.encre },
    indexe: { label: "Indexé", bg: C.vertFond, fg: C.vert },
    erreur: { label: "Erreur d'indexation", bg: C.rougeFond, fg: C.rouge },
  };
  const s = map[statut] || map.en_traitement;
  return (
    <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ backgroundColor: s.bg, color: s.fg }}>
      {s.label}
    </span>
  );
}

function FormulaireDepotNotes({ token, classes, onDepose }) {
  const [ouvert, setOuvert] = useState(false);
  const [titre, setTitre] = useState("");
  const [niveauId, setNiveauId] = useState("");
  const [matiereId, setMatiereId] = useState("");
  const [fichier, setFichier] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);

  // Niveaux et matières déduits des propres affectations de l'enseignant —
  // il ne dépose des notes que sur ce qu'il enseigne réellement.
  const niveaux = [...new Map(classes.map((c) => [c.niveau_id, c.niveau])).entries()];
  const matieres = [...new Map(classes.map((c) => [c.matiere_id, c.matiere])).entries()];

  async function soumettre(e) {
    e.preventDefault();
    if (!fichier) { setErreur("Choisissez un fichier PDF."); return; }
    setEnvoi(true); setErreur(null);
    try {
      const formData = new FormData();
      formData.append("fichier", fichier);
      await apiFetch("/enseignant/documents", {
        method: "POST", token, params: { titre, niveau_id: niveauId || undefined, matiere_id: matiereId || undefined },
        body: formData,
      });
      setTitre(""); setNiveauId(""); setMatiereId(""); setFichier(null); setOuvert(false);
      onDepose();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  if (!ouvert) {
    return (
      <button onClick={() => setOuvert(true)} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.accentFonce }}>
        <Plus size={13} /> Déposer mes notes de cours
      </button>
    );
  }

  return (
    <form onSubmit={soumettre} className="rounded-lg p-4 border space-y-2.5" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
      <BandeauErreur message={erreur} />
      <input required value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Titre (ex : Mes notes sur les fractions)"
        className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
      <div className="grid grid-cols-2 gap-2">
        <select value={niveauId} onChange={(e) => setNiveauId(e.target.value)} className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
          <option value="">Niveau (optionnel)...</option>
          {niveaux.map(([id, nom]) => <option key={id} value={id}>{nom}</option>)}
        </select>
        <select value={matiereId} onChange={(e) => setMatiereId(e.target.value)} className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
          <option value="">Matière (optionnel)...</option>
          {matieres.map(([id, nom]) => <option key={id} value={id}>{nom}</option>)}
        </select>
      </div>
      <label className="eduai-focus flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium border cursor-pointer w-fit" style={{ borderColor: C.ligne, color: C.encre, backgroundColor: C.surface }}>
        <Upload size={12} />
        {fichier ? fichier.name : "Choisir un PDF"}
        <input type="file" accept="application/pdf" className="hidden" onChange={(e) => setFichier(e.target.files[0] || null)} />
      </label>
      <p className="text-xs" style={{ color: C.encreAttenue }}>
        Privé par défaut — visible seulement par vous, jusqu'à ce que vous le partagiez explicitement avec un collègue.
      </p>
      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={envoi} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {envoi ? <Loader2 size={12} className="eduai-spin" /> : "Déposer"}
        </button>
        <button type="button" onClick={() => setOuvert(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
      </div>
    </form>
  );
}

function PanneauPartage({ token, documentId, onFerme }) {
  const [collegues, setCollegues] = useState([]);
  const [partages, setPartages] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [enCours, setEnCours] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    Promise.all([
      apiFetch("/enseignant/documents/collegues", { token }),
      apiFetch(`/enseignant/documents/${documentId}/partages`, { token }),
    ]).then(([c, p]) => { setCollegues(c); setPartages(p); })
      .catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token, documentId]);

  useEffect(() => { charger(); }, [charger]);

  const idsPartages = new Set(partages.map((p) => p.id));

  async function partagerAvec(utilisateurId) {
    setEnCours(utilisateurId); setErreur(null);
    try {
      await apiFetch(`/enseignant/documents/${documentId}/partager`, { method: "POST", token, body: { utilisateur_id: utilisateurId } });
      charger();
    } catch (e) { setErreur(e.message); }
    finally { setEnCours(null); }
  }

  async function revoquer(utilisateurId) {
    setEnCours(utilisateurId); setErreur(null);
    try {
      await apiFetch(`/enseignant/documents/${documentId}/partager/${utilisateurId}`, { method: "DELETE", token });
      charger();
    } catch (e) { setErreur(e.message); }
    finally { setEnCours(null); }
  }

  return (
    <div className="mt-2 rounded-lg border p-3" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
      <div className="flex items-center justify-between mb-2.5">
        <p className="text-xs font-semibold" style={{ color: C.encre }}>Partager avec...</p>
        <button onClick={onFerme} className="eduai-focus text-xs" style={{ color: C.encreAttenue }}>Fermer</button>
      </div>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : collegues.length === 0 ? (
        <p className="text-xs" style={{ color: C.encreAttenue }}>Aucun autre enseignant dans votre établissement pour l'instant.</p>
      ) : (
        <div className="space-y-1.5">
          {collegues.map((c) => {
            const partage = idsPartages.has(c.id);
            return (
              <div key={c.id} className="flex items-center justify-between text-xs">
                <span style={{ color: C.encre }}>{c.prenom} {c.nom}</span>
                <button
                  onClick={() => (partage ? revoquer(c.id) : partagerAvec(c.id))}
                  disabled={enCours === c.id}
                  className="eduai-focus rounded-full px-2.5 py-1 font-medium disabled:opacity-60"
                  style={partage
                    ? { backgroundColor: C.vertFond, color: C.vert }
                    : { border: `1px solid ${C.ligne}`, color: C.encreDoux }}
                >
                  {enCours === c.id ? <Loader2 size={10} className="eduai-spin" /> : partage ? "Partagé — révoquer" : "Partager"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EcranMesDocuments({ token, classes }) {
  const [documents, setDocuments] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [panneauOuvertPour, setPanneauOuvertPour] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/enseignant/documents", { token })
      .then(setDocuments).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function supprimer(id) {
    try {
      await apiFetch(`/enseignant/documents/${id}`, { method: "DELETE", token });
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (e) { setErreur(e.message); }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Mes documents</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        Vos notes de cours, utilisées par l'IA pour ancrer ses générations. Privées par défaut — un document que vous
        déposez n'est visible que par vous, jusqu'à ce que vous le partagiez explicitement avec un collègue de votre établissement.
      </p>

      <BandeauErreur message={erreur} />

      <div className="rounded-2xl p-6 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <h2 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Notes de cours</h2>

        <FormulaireDepotNotes token={token} classes={classes} onDepose={charger} />

        {chargement ? <Chargement /> : (
          <div className="space-y-2 mt-5">
            {documents.map((d) => (
              <div key={d.id} className="rounded-lg border px-3 py-2.5" style={{ borderColor: C.ligne }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileText size={15} color={C.encreAttenue} className="flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: C.encre }}>{d.titre}</p>
                      <p className="text-xs" style={{ color: C.encreAttenue }}>
                        {[d.niveau, d.matiere].filter(Boolean).join(" · ") || "Niveau/matière non précisés"}
                        {!d.est_proprietaire && " · Partagé avec vous"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <BadgeStatutDocument statut={d.statut} />
                    {d.est_proprietaire ? (
                      <>
                        <button onClick={() => setPanneauOuvertPour(panneauOuvertPour === d.id ? null : d.id)}
                          className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.accentFonce }}>
                          <Share2 size={12} /> Partager
                        </button>
                        <button onClick={() => supprimer(d.id)} className="eduai-focus" aria-label="Supprimer" style={{ color: C.encreAttenue }}>
                          <Trash2 size={14} />
                        </button>
                      </>
                    ) : (
                      <span className="text-xs italic" style={{ color: C.encreAttenue }}>Lecture seule</span>
                    )}
                  </div>
                </div>
                {panneauOuvertPour === d.id && (
                  <PanneauPartage token={token} documentId={d.id} onFerme={() => setPanneauOuvertPour(null)} />
                )}
              </div>
            ))}
            {documents.length === 0 && (
              <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucune note de cours déposée pour l'instant.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Génération libre (sans classe, sans établissement)         */
/* ------------------------------------------------------------------ */

function CarteExerciceGenereLibre({ exercice, onStatutChange }) {
  const [ouvertCorrige, setOuvertCorrige] = useState(false);
  const [enCours, setEnCours] = useState(false);

  async function changerStatut(nouveauStatut) {
    setEnCours(true);
    try { await onStatutChange(exercice.id, nouveauStatut); }
    finally { setEnCours(false); }
  }

  const badge = {
    en_attente: { label: "À relire", bg: C.ambreFond, fg: C.ambre },
    valide: { label: "Validé", bg: C.vertFond, fg: C.vert },
    rejete: { label: "Rejeté", bg: C.rougeFond, fg: C.rouge },
  }[exercice.statut];

  return (
    <div className="rounded-xl p-5 border eduai-fade-in" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="eduai-display text-base" style={{ color: C.encre }}>{exercice.theme}</h3>
          {exercice.sous_theme && <p className="text-xs" style={{ color: C.encreAttenue }}>{exercice.sous_theme}</p>}
        </div>
        <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full flex-shrink-0" style={{ backgroundColor: badge.bg, color: badge.fg }}>{badge.label}</span>
      </div>

      <p className="text-sm font-semibold mb-1 mt-3" style={{ color: C.encre }}>Énoncé</p>
      <p className="text-sm mb-3 whitespace-pre-wrap" style={{ color: C.encreDoux }}>{exercice.enonce}</p>

      <button onClick={() => setOuvertCorrige((o) => !o)} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-3" style={{ color: C.accentFonce }}>
        <ChevronDown size={12} style={{ transform: ouvertCorrige ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />
        {ouvertCorrige ? "Masquer le corrigé" : "Voir le corrigé"}
      </button>
      {ouvertCorrige && (
        <div className="pt-2 border-t mb-3" style={{ borderColor: C.ligne }}>
          <p className="text-sm whitespace-pre-wrap mb-2" style={{ color: C.encreDoux }}>{exercice.corrige}</p>
          {exercice.etapes?.length > 0 && (
            <ul className="list-disc list-inside text-sm space-y-0.5" style={{ color: C.encreDoux }}>
              {exercice.etapes.map((et, i) => <li key={i}>{et}</li>)}
            </ul>
          )}
        </div>
      )}

      {exercice.tags?.length > 0 && (
        <div className="flex gap-1.5 flex-wrap mb-3">
          {exercice.tags.map((t) => <span key={t} className="rounded-full px-2 py-0.5 text-[11px]" style={{ backgroundColor: C.bleuFond, color: C.encre }}>{t}</span>)}
        </div>
      )}

      {exercice.statut === "en_attente" && (
        <div className="flex gap-2 pt-1">
          <button onClick={() => changerStatut("valide")} disabled={enCours}
            className="eduai-focus flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-60" style={{ backgroundColor: C.vertFond, color: C.vert }}>
            <Check size={12} /> Valider
          </button>
          <button onClick={() => changerStatut("rejete")} disabled={enCours}
            className="eduai-focus flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-60" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
            <XIcon size={12} /> Rejeter
          </button>
        </div>
      )}
    </div>
  );
}

function EcranGenerationLibre({ token }) {
  const [matieres, setMatieres] = useState([]);
  const [matiereId, setMatiereId] = useState("");
  const [niveau, setNiveau] = useState("");
  const [theme, setTheme] = useState("");
  const [quantite, setQuantite] = useState(3);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState(null);

  const [historique, setHistorique] = useState([]);
  const [chargementHistorique, setChargementHistorique] = useState(true);

  useEffect(() => {
    apiFetch("/enseignant/matieres", { token }).then((m) => { setMatieres(m); if (m[0]) setMatiereId(m[0].id); }).catch(() => {});
  }, [token]);

  const chargerHistorique = useCallback(() => {
    setChargementHistorique(true);
    apiFetch("/enseignant/generation-libre", { token }).then(setHistorique).catch(() => {}).finally(() => setChargementHistorique(false));
  }, [token]);

  useEffect(() => { chargerHistorique(); }, [chargerHistorique]);

  async function generer(e) {
    e.preventDefault();
    setEnCours(true); setErreur(null);
    try {
      await apiFetch("/enseignant/generation-libre", {
        method: "POST", token, body: { matiere_id: matiereId, niveau, theme, quantite: Number(quantite) },
      });
      setTheme("");
      chargerHistorique();
    } catch (e) { setErreur(e.message); }
    finally { setEnCours(false); }
  }

  async function changerStatut(exerciceId, statut) {
    try {
      await apiFetch(`/enseignant/generation-libre/${exerciceId}`, { method: "PATCH", token, body: { statut } });
      chargerHistorique();
    } catch (e) { setErreur(e.message); }
  }

  const enAttente = historique.filter((e) => e.statut === "en_attente");
  const traites = historique.filter((e) => e.statut !== "en_attente");

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Génération libre</h1>
      <p className="text-sm mb-2" style={{ color: C.encreDoux }}>
        Génère une série d'exercices corrigés sur le niveau et le thème de ton choix — utile pour préparer du contenu sur
        plusieurs classes que tu enseignes, sans dépendre d'une classe déclarée. Une fois validés, ils enrichissent
        silencieusement le corpus utilisé par l'IA. Toujours gratuit, quel que soit ton solde de crédits.
      </p>
      <p className="flex items-center gap-1.5 text-xs mb-8" style={{ color: C.encreAttenue }}>
        <AlertTriangle size={11} /> EduAI peut faire des erreurs, toujours vérifier les informations et surtout valider les exercices avant de les mettre à la disposition des élèves.
      </p>

      <BandeauErreur message={erreur} />

      <form onSubmit={generer} className="rounded-2xl p-6 border space-y-3 mb-8" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <div className="grid grid-cols-2 gap-3">
          <select value={matiereId} onChange={(e) => setMatiereId(e.target.value)} required
            className="eduai-focus rounded-lg px-3 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
            {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom}</option>)}
          </select>
          <input required value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="Niveau (ex : Terminale D)"
            className="eduai-focus rounded-lg px-3 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
        </div>
        <input required value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="Thème (ex : les suites numériques)"
          className="eduai-focus w-full rounded-lg px-3 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
        <label className="flex items-center gap-3">
          <span className="text-xs font-medium" style={{ color: C.encreDoux }}>Nombre d'exercices</span>
          <select value={quantite} onChange={(e) => setQuantite(e.target.value)}
            className="eduai-focus rounded-lg px-3 py-1.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <button type="submit" disabled={enCours}
          className="eduai-focus flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {enCours ? <Loader2 size={14} className="eduai-spin" /> : <Wand2 size={14} />} Générer
        </button>
      </form>

      {chargementHistorique ? <Chargement /> : (
        <>
          {enAttente.length > 0 && (
            <div className="mb-8">
              <h2 className="eduai-display text-lg mb-3" style={{ color: C.encre }}>À relire ({enAttente.length})</h2>
              <div className="space-y-4">
                {enAttente.map((ex) => <CarteExerciceGenereLibre key={ex.id} exercice={ex} onStatutChange={changerStatut} />)}
              </div>
            </div>
          )}

          {traites.length > 0 && (
            <div>
              <h2 className="eduai-display text-lg mb-3" style={{ color: C.encre }}>Historique</h2>
              <div className="space-y-4">
                {traites.map((ex) => <CarteExerciceGenereLibre key={ex.id} exercice={ex} onStatutChange={changerStatut} />)}
              </div>
            </div>
          )}

          {historique.length === 0 && (
            <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucun exercice généré pour l'instant.</p>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Invitations reçues d'un établissement                      */
/* ------------------------------------------------------------------ */

function EcranInvitations({ token, onTraitee }) {
  const [invitations, setInvitations] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [enCours, setEnCours] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/enseignant/invitations", { token }).then(setInvitations).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function repondre(id, accepter) {
    setEnCours(id); setErreur(null);
    try {
      await apiFetch(`/enseignant/invitations/${id}/${accepter ? "accepter" : "refuser"}`, { method: "POST", token });
      charger();
      onTraitee?.();
    } catch (e) { setErreur(e.message); }
    finally { setEnCours(null); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Invitations</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>Établissements qui t'invitent à les rejoindre.</p>

      <BandeauErreur message={erreur} />

      {chargement ? <Chargement /> : (
        <div className="space-y-3">
          {invitations.map((inv) => (
            <div key={inv.id} className="rounded-2xl p-5 border flex items-center justify-between" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div>
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{inv.etablissement_nom}</p>
                <p className="text-xs" style={{ color: C.encreAttenue }}>
                  {inv.classe_nom
                    ? `t'invite à enseigner ${inv.matiere_nom} en ${inv.classe_nom}`
                    : "t'invite à rejoindre son établissement"}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => repondre(inv.id, true)} disabled={enCours === inv.id}
                  className="eduai-focus rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                  Accepter
                </button>
                <button onClick={() => repondre(inv.id, false)} disabled={enCours === inv.id}
                  className="eduai-focus rounded-lg px-3 py-1.5 text-xs font-medium border" style={{ borderColor: C.ligne, color: C.encreDoux }}>
                  Refuser
                </button>
              </div>
            </div>
          ))}
          {invitations.length === 0 && <p className="text-sm text-center py-10" style={{ color: C.encreAttenue }}>Aucune invitation en attente.</p>}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Mes crédits                                                 */
/* ------------------------------------------------------------------ */

const LABELS_MOTIF = {
  validation_simple: "Ressource validée",
  validation_corrigee: "Ressource corrigée puis validée",
  depot_cours: "Cours déposé",
};

function EcranMesCredits({ token }) {
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    apiFetch("/enseignant/credits", { token }).then(setDonnees).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  if (chargement) return <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10"><Chargement /></div>;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Mes crédits</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        Gagnés en validant vos ressources — la Génération libre reste toujours gratuite, quel que soit votre solde.
      </p>

      <BandeauErreur message={erreur} />

      {donnees && (
        <>
          <div className="rounded-2xl p-7 border mb-6 text-center" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
            <p className="eduai-display text-5xl mb-1" style={{ color: C.encre }}>{donnees.solde}</p>
            <p className="text-xs" style={{ color: C.encreAttenue }}>crédit{donnees.solde !== 1 ? "s" : ""}</p>
            {donnees.en_periode_gratuite ? (
              <div className="mt-4 rounded-lg px-3 py-2 text-xs inline-flex items-center gap-1.5" style={{ backgroundColor: C.vertFond, color: C.vert }}>
                <Check size={12} /> Période gratuite — Déposer un cours reste illimité pour l'instant
              </div>
            ) : (
              <div className="mt-4 rounded-lg px-3 py-2 text-xs" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                Chaque dépôt de cours coûte 2 crédits — validez des ressources pour en gagner
              </div>
            )}
          </div>

          <h2 className="eduai-display text-lg mb-3" style={{ color: C.encre }}>Historique récent</h2>
          <div className="space-y-1.5">
            {donnees.historique.map((h, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border px-3 py-2.5" style={{ borderColor: C.ligne }}>
                <span className="text-sm" style={{ color: C.encre }}>{LABELS_MOTIF[h.motif] || h.motif}</span>
                <span className="eduai-mono text-xs font-semibold" style={{ color: h.delta > 0 ? C.vert : C.rouge }}>
                  {h.delta > 0 ? "+" : ""}{h.delta}
                </span>
              </div>
            ))}
            {donnees.historique.length === 0 && <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucun mouvement pour l'instant.</p>}
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Application                                                        */
/* ------------------------------------------------------------------ */

export default function App() {
  const [token, setToken] = useState(null);
  const [connexionEnCours, setConnexionEnCours] = useState(false);
  const [erreurConnexion, setErreurConnexion] = useState(null);

  const [vue, setVue] = useState("accueil");
  const [chargementInitial, setChargementInitial] = useState(false);

  const [enAttente, setEnAttente] = useState([]);
  const [chargementFile, setChargementFile] = useState(true);
  const [erreurFile, setErreurFile] = useState(null);
  const [filtre, setFiltre] = useState(null);
  const [exerciceActifId, setExerciceActifId] = useState(null);
  const [historique, setHistorique] = useState([]);

  const [cours, setCours] = useState([]);
  const [chargementCours, setChargementCours] = useState(true);
  const [erreurCours, setErreurCours] = useState(null);
  const [coursActifId, setCoursActifId] = useState(null);

  const [classes, setClasses] = useState([]);
  const [chargementClasses, setChargementClasses] = useState(true);
  const [erreurClasses, setErreurClasses] = useState(null);
  const [classeActive, setClasseActive] = useState(null);
  const [eleveActif, setEleveActif] = useState(null);

  const [nombreInvitations, setNombreInvitations] = useState(0);

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      // Vérifie le rôle avant d'afficher quoi que ce soit — cet espace lance
      // plusieurs chargements en parallèle après connexion, plus simple et
      // plus sûr de vérifier une fois ici que de dédupliquer 401 x3.
      await apiFetch("/enseignant/matieres", { token: access_token });
      setToken(access_token);
    } catch (e) {
      setErreurConnexion(e.status === 401 ? "Ce compte n'a pas accès à cet espace." : e.message);
    }
    finally { setConnexionEnCours(false); }
  }

  async function inscrire(payload) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/inscription-enseignant", { method: "POST", body: payload });
      setToken(access_token);
    } catch (e) { setErreurConnexion(e.message); }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() {
    setToken(null); setVue("accueil");
    setEnAttente([]); setCours([]); setClasses([]); setHistorique([]); setNombreInvitations(0);
  }

  // Chargement initial une fois connecté : file de validation, cours, classes
  useEffect(() => {
    if (!token) return;
    setChargementInitial(true);
    setChargementFile(true); setChargementCours(true); setChargementClasses(true);

    apiFetch("/enseignant/exercices/a-valider", { token })
      .then(setEnAttente).catch((e) => setErreurFile(e.message)).finally(() => setChargementFile(false));

    apiFetch("/enseignant/cours", { token })
      .then(setCours).catch((e) => setErreurCours(e.message)).finally(() => setChargementCours(false));

    apiFetch("/enseignant/mes-classes", { token })
      .then(setClasses).catch((e) => setErreurClasses(e.message)).finally(() => setChargementClasses(false));

    apiFetch("/enseignant/invitations", { token }).then((inv) => setNombreInvitations(inv.length)).catch(() => {});

    setChargementInitial(false);
  }, [token]);

  async function onValider(id) {
    const ex = enAttente.find((e) => e.id === id);
    await apiFetch(`/enseignant/exercices/${id}/valider`, { method: "POST", token });
    setEnAttente((prev) => prev.filter((e) => e.id !== id));
    setHistorique((prev) => [{ ...ex, statut: "valide" }, ...prev]);
  }

  async function onRejeter(id, motif) {
    const ex = enAttente.find((e) => e.id === id);
    await apiFetch(`/enseignant/exercices/${id}/rejeter`, { method: "POST", token, body: { motif } });
    setEnAttente((prev) => prev.filter((e) => e.id !== id));
    setHistorique((prev) => [{ ...ex, statut: "rejete", motif }, ...prev]);
  }

  function onCoursDepose(nouveauCours) {
    setCoursActifId(nouveauCours.id);
    apiFetch("/enseignant/cours", { token }).then(setCours).catch(() => {});
  }

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>

      {!token ? (
        <EcranConnexion onConnexion={connecter} onInscription={inscrire} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} nombreEnAttente={enAttente.length} nombreInvitations={nombreInvitations} />
          {vue === "accueil" && <EcranAccueil setVue={setVue} enAttente={enAttente} historique={historique} cours={cours} classes={classes} />}

          {vue === "mes-cours" && <EcranMesCours cours={cours} chargement={chargementCours} erreur={erreurCours} setVue={setVue} setCoursActifId={setCoursActifId} classes={classes} />}
          {vue === "deposer-cours" && <EcranDeposerCours classes={classes} token={token} setVue={setVue} onCoursDepose={onCoursDepose} />}
          {vue === "cours-detail" && coursActifId && <EcranCoursDetail coursId={coursActifId} token={token} setVue={setVue} />}
          {vue === "generation-libre" && <EcranGenerationLibre token={token} />}
          {vue === "mes-credits" && <EcranMesCredits token={token} />}
          {vue === "invitations" && <EcranInvitations token={token} onTraitee={() => apiFetch("/enseignant/invitations", { token }).then((inv) => setNombreInvitations(inv.length)).catch(() => {})} />}

          {vue === "mes-classes" && <EcranMesClasses classes={classes} chargement={chargementClasses} erreur={erreurClasses} setVue={setVue} setClasseActive={setClasseActive} token={token} />}
          {vue === "mes-documents" && <EcranMesDocuments token={token} classes={classes} />}
          {vue === "classe-detail" && classeActive && <EcranClasseDetail classeActive={classeActive} token={token} setVue={setVue} setEleveActif={setEleveActif} />}
          {vue === "eleve-detail" && eleveActif && classeActive && <EcranEleveDetail eleveActif={eleveActif} classeActive={classeActive} token={token} setVue={setVue} />}

          {vue === "file" && <EcranFile enAttente={enAttente} chargement={chargementFile} erreur={erreurFile} setExerciceActifId={setExerciceActifId} setVue={setVue} filtre={filtre} setFiltre={setFiltre} />}
          {vue === "exercice-detail" && exerciceActifId && <EcranExerciceDetail exerciceId={exerciceActifId} enAttente={enAttente} token={token} setVue={setVue} onValider={onValider} onRejeter={onRejeter} />}

          {vue === "historique" && <EcranHistorique token={token} />}
        </>
      )}
    </div>
  );
}
