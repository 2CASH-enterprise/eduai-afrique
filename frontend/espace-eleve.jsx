import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen, Calculator, FlaskConical, Leaf, Landmark, Languages,
  ChevronRight, ChevronLeft, LogOut, Bell, TrendingUp, CalendarClock,
  Check, X as XIcon, Sparkles, GraduationCap, Lock, Mail, Loader2, AlertTriangle,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Configuration API                                                  */
/* ------------------------------------------------------------------ */

const API_BASE_URL = "http://178.104.56.200:8000";

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
  let reponse;
  try {
    reponse = await fetch(url, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ErreurApi(`Impossible de joindre l'API (${API_BASE_URL}). Vérifiez qu'elle tourne et que CORS est activé.`);
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
/*  Constantes d'affichage (icônes/texture papier par matière)         */
/* ------------------------------------------------------------------ */

const ICONES_MATIERE = {
  "Mathématiques": { icon: Calculator, papier: "grille" },
  "Physique-Chimie": { icon: FlaskConical, papier: "grille" },
  "SVT": { icon: Leaf, papier: "lignes" },
  "Histoire-Géographie": { icon: Landmark, papier: "lignes" },
  "Français": { icon: Languages, papier: "lignes" },
};
function infoMatiere(nom) {
  return ICONES_MATIERE[nom] || { icon: BookOpen, papier: "lignes" };
}

const DIFFICULTE_LABEL = { facile: "Facile", moyen: "Moyen", difficile: "Difficile" };

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

  .eduai-stamp { animation: eduai-stamp-in 420ms cubic-bezier(0.2, 1.4, 0.4, 1) forwards; }
  @keyframes eduai-stamp-in {
    0%   { opacity: 0; transform: scale(1.6) rotate(-14deg); }
    60%  { opacity: 1; transform: scale(0.95) rotate(-5deg); }
    100% { opacity: 1; transform: scale(1) rotate(-6deg); }
  }

  .eduai-fade-in { animation: eduai-fade 320ms ease-out forwards; }
  @keyframes eduai-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  .eduai-spin { animation: eduai-spin 1.1s linear infinite; }
  @keyframes eduai-spin { to { transform: rotate(360deg); } }

  @media (prefers-reduced-motion: reduce) {
    .eduai-stamp, .eduai-fade-in { animation: none !important; }
    .eduai-spin { animation-duration: 2.4s; }
  }

  .eduai-focus:focus-visible { outline: 2px solid #B08D57; outline-offset: 2px; border-radius: 6px; }
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

function Chargement({ label = "Chargement..." }) {
  return (
    <div className="flex items-center gap-2 py-10 justify-center" style={{ color: C.encreDoux }}>
      <Loader2 size={16} className="eduai-spin" /><span className="text-sm">{label}</span>
    </div>
  );
}
function BandeauErreur({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-lg px-4 py-3 mb-4 flex items-start gap-2 text-sm" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
      <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" /><span>{message}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Connexion                                                   */
/* ------------------------------------------------------------------ */

function EcranConnexion({ onConnexion, connexionEnCours, erreurConnexion }) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");

  return (
    <div className="min-h-screen flex items-center justify-center px-6 eduai-root" style={{ backgroundColor: C.fond }}>
      <div className="w-full max-w-sm eduai-fade-in">
        <div className="flex items-center gap-2 mb-10 justify-center">
          <GraduationCap size={26} color={C.encre} strokeWidth={1.75} />
          <span className="eduai-display text-2xl" style={{ color: C.encre }}>
            Oskar<span style={{ color: C.accent }}>AI</span>
          </span>
        </div>

        <div className="rounded-2xl p-8 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Content de te revoir</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Connecte-toi pour retrouver tes exercices.</p>

          <BandeauErreur message={erreurConnexion} />

          <form onSubmit={(e) => { e.preventDefault(); onConnexion(email, motDePasse); }} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}>
                <Mail size={13} /> Adresse email
              </span>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="jean.dupont@ecole.cm"
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

            <button
              type="submit" disabled={connexionEnCours}
              className="eduai-focus w-full flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold mt-2 transition-colors disabled:opacity-60"
              style={{ backgroundColor: C.encre, color: C.surface }}
            >
              {connexionEnCours && <Loader2 size={14} className="eduai-spin" />} Se connecter
            </button>
          </form>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: C.encreAttenue }}>API : <span className="eduai-mono">{API_BASE_URL}</span></p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Barre de navigation + panneau notifications                        */
/* ------------------------------------------------------------------ */

function PanneauNotifications({ token, ouvert, onFermer }) {
  const [notifs, setNotifs] = useState([]);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    if (!ouvert) return;
    setChargement(true);
    apiFetch("/eleve/notifications", { token }).then(setNotifs).catch(() => {}).finally(() => setChargement(false));
  }, [ouvert, token]);

  async function marquerLue(id) {
    try {
      await apiFetch(`/eleve/notifications/${id}/lu`, { method: "PATCH", token });
      setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, lue: true } : n)));
    } catch { /* silencieux */ }
  }

  if (!ouvert) return null;
  return (
    <div className="absolute right-4 sm:right-8 top-14 z-20 w-80 rounded-xl border eduai-fade-in" style={{ backgroundColor: C.surface, borderColor: C.ligne, boxShadow: C.surfaceOmbre }}>
      <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: C.ligne }}>
        <span className="text-sm font-semibold" style={{ color: C.encre }}>Notifications</span>
        <button onClick={onFermer} className="eduai-focus"><XIcon size={14} color={C.encreDoux} /></button>
      </div>
      <div className="max-h-80 overflow-y-auto">
        {chargement ? <Chargement /> : notifs.length === 0 ? (
          <p className="text-sm px-4 py-6" style={{ color: C.encreDoux }}>Rien de nouveau.</p>
        ) : notifs.map((n) => (
          <button key={n.id} onClick={() => marquerLue(n.id)} className="eduai-focus w-full text-left px-4 py-3 border-b last:border-b-0"
            style={{ borderColor: C.ligne, backgroundColor: n.lue ? "transparent" : C.bleuFond }}>
            <p className="text-xs font-semibold" style={{ color: C.encre }}>{n.titre}</p>
            <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{n.message}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function BarreNav({ vue, setVue, onDeconnexion, token }) {
  const [notifsOuvertes, setNotifsOuvertes] = useState(false);
  const items = [
    { id: "accueil", label: "Accueil" },
    { id: "exercices", label: "Exercices" },
    { id: "resultats", label: "Résultats" },
  ];
  return (
    <div className="relative">
      <div
        className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b"
        style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}
      >
        <button onClick={() => setVue("accueil")} className="eduai-focus flex items-center gap-2">
          <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
          <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>OskarAI</span>
        </button>

        <nav className="flex items-center gap-5">
          {items.map((it) => (
            <button
              key={it.id}
              onClick={() => setVue(it.id)}
              className="eduai-focus relative pb-1 text-xs font-medium transition-colors"
              style={{ color: vue === it.id ? C.encre : C.encreAttenue }}
            >
              {it.label}
              {vue === it.id && <span className="absolute left-0 right-0 -bottom-[15px] h-[2px]" style={{ backgroundColor: C.accent }} />}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <button onClick={() => setNotifsOuvertes((v) => !v)} className="eduai-focus relative" aria-label="Notifications">
            <Bell size={17} color={C.encreDoux} />
          </button>
          <button onClick={onDeconnexion} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.encreDoux }}>
            <LogOut size={14} />
            <span className="hidden sm:inline">Déconnexion</span>
          </button>
        </div>
      </div>
      <PanneauNotifications token={token} ouvert={notifsOuvertes} onFermer={() => setNotifsOuvertes(false)} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Accueil                                                     */
/* ------------------------------------------------------------------ */

function EcranAccueil({ setVue, exercices, resultats, planning, chargement, erreur }) {
  const moyenneGenerale = resultats.length
    ? (resultats.reduce((s, r) => s + r.moyenne_sur_20, 0) / resultats.length).toFixed(1)
    : null;

  if (chargement) return <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10"><Chargement label="Chargement..." /></div>;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Bonjour !</h1>

      <BandeauErreur message={erreur} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <CarteStat label="Moyenne générale" valeur={moyenneGenerale === null ? "—" : `${moyenneGenerale}/20`} icon={TrendingUp} />
        <CarteStat label="Exercices disponibles" valeur={exercices.length} icon={BookOpen} />
        <CarteStat label="Devoirs à venir" valeur={planning.length} icon={CalendarClock} />
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="eduai-display text-lg" style={{ color: C.encre }}>À rendre prochainement</h2>
        <button onClick={() => setVue("exercices")} className="eduai-focus text-xs font-medium flex items-center gap-1" style={{ color: C.accentFonce }}>
          Voir tous les exercices <ChevronRight size={14} />
        </button>
      </div>

      <div className="space-y-3">
        {planning.map((d) => (
          <div key={d.id} className="rounded-xl px-5 py-4 flex items-center justify-between" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
            <div>
              <p className="text-sm font-semibold" style={{ color: C.encre }}>{d.titre}</p>
              <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{d.matiere}</p>
            </div>
            <div className="eduai-mono text-xs px-2.5 py-1 rounded-full" style={{ backgroundColor: C.ambreFond, color: C.ambre }}>
              {new Date(d.date_limite).toLocaleDateString("fr-FR")}
            </div>
          </div>
        ))}
        {planning.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun devoir à venir.</p>}
      </div>
    </div>
  );
}

function CarteStat({ label, valeur, icon: Icon }) {
  return (
    <div className="rounded-xl p-5" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: C.encreDoux }}>{label}</span>
        <Icon size={15} color={C.encreAttenue} />
      </div>
      <p className="eduai-display text-2xl" style={{ color: C.encre }}>{valeur}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Liste des exercices                                        */
/* ------------------------------------------------------------------ */

function EcranExercices({ setVue, setExerciceActifId, filtre, setFiltre, exercices, chargement, erreur }) {
  const exercicesFiltres = filtre ? exercices.filter((e) => e.matiere === filtre) : exercices;
  const matieresPresentes = [...new Set(exercices.map((e) => e.matiere))];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-6" style={{ color: C.encre }}>Exercices</h1>

      <BandeauErreur message={erreur} />

      <div className="flex gap-2 mb-8 overflow-x-auto pb-1">
        <ChipMatiere label="Toutes" active={!filtre} onClick={() => setFiltre(null)} />
        {matieresPresentes.map((m) => {
          const { icon } = infoMatiere(m);
          return <ChipMatiere key={m} label={m} active={filtre === m} onClick={() => setFiltre(m)} icon={icon} />;
        })}
      </div>

      {chargement ? <Chargement label="Chargement des exercices..." /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {exercicesFiltres.map((ex) => {
            const { icon: Icon, papier } = infoMatiere(ex.matiere);
            const badge = badgeColorForDifficulte(ex.difficulte);
            return (
              <button
                key={ex.id}
                onClick={() => { setExerciceActifId(ex.id); setVue("exercice-detail"); }}
                className={`eduai-focus text-left rounded-xl p-5 eduai-paper-${papier} transition-transform hover:-translate-y-0.5`}
                style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderLeft: `3px solid ${C.accent}` }}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon size={16} color={C.encre} />
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: badge.bg, color: badge.fg }}>
                    {DIFFICULTE_LABEL[ex.difficulte]}
                  </span>
                </div>
                <p className="text-xs font-medium mb-1.5" style={{ color: C.encreDoux }}>{ex.matiere} · {ex.theme}</p>
                <p className="text-sm leading-snug" style={{ color: C.encre }}>{ex.enonce}</p>
              </button>
            );
          })}
          {exercicesFiltres.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun exercice disponible pour l'instant.</p>}
        </div>
      )}
    </div>
  );
}

function ChipMatiere({ label, active, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className="eduai-focus flex items-center gap-1.5 whitespace-nowrap px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors"
      style={{ backgroundColor: active ? C.encre : C.surface, color: active ? C.surface : C.encreDoux, border: `1px solid ${active ? C.encre : C.ligne}` }}
    >
      {Icon && <Icon size={13} />}
      {label}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail d'un exercice (révélation + tentative réelles)      */
/* ------------------------------------------------------------------ */

function EcranExerciceDetail({ exerciceId, exercices, token, setVue }) {
  const ex = exercices.find((e) => e.id === exerciceId);
  const { papier } = infoMatiere(ex?.matiere);
  const badge = badgeColorForDifficulte(ex?.difficulte);

  const [revele, setRevele] = useState(false);
  const [corrige, setCorrige] = useState("");
  const [etapes, setEtapes] = useState([]);
  const [chargementRevele, setChargementRevele] = useState(false);
  const [tentative, setTentative] = useState(null);
  const [envoiTentative, setEnvoiTentative] = useState(false);
  const [erreur, setErreur] = useState(null);
  const debutRef = useRef(Date.now());

  if (!ex) return null;

  async function reveler() {
    setChargementRevele(true); setErreur(null);
    try {
      const r = await apiFetch(`/eleve/exercices/${ex.id}/reveler`, { method: "POST", token });
      setCorrige(r.corrige); setEtapes(r.etapes || []); setRevele(true);
    } catch (e) { setErreur(e.message); }
    finally { setChargementRevele(false); }
  }

  async function declarerTentative(reussi) {
    setEnvoiTentative(true); setErreur(null);
    try {
      const temps = Math.round((Date.now() - debutRef.current) / 1000);
      await apiFetch(`/eleve/exercices/${ex.id}/tentative`, { method: "POST", token, body: { reussi, temps_passe_secondes: temps } });
      setTentative(reussi);
    } catch (e) { setErreur(e.message); }
    finally { setEnvoiTentative(false); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("exercices")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour aux exercices
      </button>

      <BandeauErreur message={erreur} />

      <div
        className={`rounded-2xl p-7 eduai-paper-${papier}`}
        style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderLeft: `4px solid ${C.rouge}` }}
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-semibold" style={{ color: C.encre }}>{ex.matiere}</span>
          <span style={{ color: "#C6BFA9" }}>·</span>
          <span className="text-xs" style={{ color: C.encreDoux }}>{ex.theme}</span>
          <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full ml-auto" style={{ backgroundColor: badge.bg, color: badge.fg }}>
            {DIFFICULTE_LABEL[ex.difficulte]}
          </span>
        </div>

        <p className="eduai-display text-lg leading-relaxed mb-8" style={{ color: C.encre }}>{ex.enonce}</p>

        {!revele && (
          <button
            onClick={reveler} disabled={chargementRevele}
            className="eduai-focus flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-60"
            style={{ backgroundColor: C.encre, color: C.surface }}
          >
            {chargementRevele ? <Loader2 size={15} className="eduai-spin" /> : <Sparkles size={15} />} Révéler le corrigé
          </button>
        )}

        {revele && (
          <div className="eduai-stamp">
            <div className="rounded-xl p-5 mb-5 relative" style={{ backgroundColor: "#FFFFFF", border: `1.5px dashed ${C.rouge}` }}>
              <span className="eduai-mono text-[10px] font-bold px-2 py-0.5 rounded absolute -top-3 left-4" style={{ backgroundColor: C.surface, color: C.rouge, border: `1.5px solid ${C.rouge}` }}>
                CORRIGÉ
              </span>
              <p className="text-base font-semibold mt-1.5 mb-4" style={{ color: C.rouge }}>{corrige}</p>
              <ol className="space-y-1.5">
                {etapes.map((etape, i) => (
                  <li key={i} className="text-sm flex gap-2" style={{ color: C.encreDoux }}>
                    <span className="eduai-mono" style={{ color: "#B8A98A" }}>{i + 1}.</span>
                    {etape}
                  </li>
                ))}
              </ol>
            </div>

            {tentative === null ? (
              <div>
                <p className="text-xs font-medium mb-2.5" style={{ color: C.encreDoux }}>As-tu trouvé la bonne réponse ?</p>
                <div className="flex gap-2.5">
                  <button onClick={() => declarerTentative(true)} disabled={envoiTentative}
                    className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60"
                    style={{ backgroundColor: C.vertFond, color: C.vert }}>
                    <Check size={15} /> Oui, réussi
                  </button>
                  <button onClick={() => declarerTentative(false)} disabled={envoiTentative}
                    className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60"
                    style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                    <XIcon size={15} /> Pas cette fois
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm font-medium flex items-center gap-1.5" style={{ color: tentative ? C.vert : C.rouge }}>
                {tentative ? <Check size={16} /> : <XIcon size={16} />}
                {tentative ? "Tentative enregistrée : réussi." : "Tentative enregistrée : à revoir."}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Résultats                                                   */
/* ------------------------------------------------------------------ */

function EcranResultats({ resultats, chargement, erreur }) {
  const max = 20;
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Mes résultats</h1>

      <BandeauErreur message={erreur} />

      {chargement ? <Chargement /> : (
        <div className="rounded-2xl p-7" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
          {resultats.length === 0 ? (
            <p className="text-sm" style={{ color: C.encreDoux }}>Aucune note enregistrée pour l'instant.</p>
          ) : (
            <div className="space-y-5">
              {resultats.map((r, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium" style={{ color: C.encre }}>{r.matiere} <span className="text-xs" style={{ color: C.encreAttenue }}>· T{r.trimestre}</span></span>
                    <span className="eduai-mono text-sm font-bold" style={{ color: C.encre }}>{r.moyenne_sur_20.toFixed(1)}/20</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: "#EDE7D6" }}>
                    <div className="h-full rounded-full transition-all duration-700" style={{ width: `${(r.moyenne_sur_20 / max) * 100}%`, backgroundColor: r.moyenne_sur_20 >= 12 ? C.vert : C.ambre }} />
                  </div>
                  <p className="text-[11px] mt-1" style={{ color: C.encreAttenue }}>{r.nombre_notes} note{r.nombre_notes !== 1 ? "s" : ""}</p>
                </div>
              ))}
            </div>
          )}
        </div>
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
  const [filtre, setFiltre] = useState(null);
  const [exerciceActifId, setExerciceActifId] = useState(null);

  const [exercices, setExercices] = useState([]);
  const [resultats, setResultats] = useState([]);
  const [planning, setPlanning] = useState([]);
  const [chargementInitial, setChargementInitial] = useState(true);
  const [erreurChargement, setErreurChargement] = useState(null);

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      setToken(access_token);
    } catch (e) { setErreurConnexion(e.message); }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() {
    setToken(null); setVue("accueil");
    setExercices([]); setResultats([]); setPlanning([]);
  }

  useEffect(() => {
    if (!token) return;
    setChargementInitial(true); setErreurChargement(null);
    Promise.all([
      apiFetch("/eleve/exercices", { token }),
      apiFetch("/eleve/mes-resultats", { token }),
      apiFetch("/eleve/mon-planning", { token }),
    ])
      .then(([ex, res, plan]) => { setExercices(ex); setResultats(res); setPlanning(plan); })
      .catch((e) => {
        if (e.status === 401) { setToken(null); setErreurConnexion("Ce compte n'a pas accès à cet espace."); }
        else setErreurChargement(e.message);
      })
      .finally(() => setChargementInitial(false));
  }, [token]);

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>

      {!token ? (
        <EcranConnexion onConnexion={connecter} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} token={token} />

          {vue === "accueil" && (
            <EcranAccueil setVue={setVue} exercices={exercices} resultats={resultats} planning={planning} chargement={chargementInitial} erreur={erreurChargement} />
          )}
          {vue === "exercices" && (
            <EcranExercices setVue={setVue} setExerciceActifId={setExerciceActifId} filtre={filtre} setFiltre={setFiltre}
              exercices={exercices} chargement={chargementInitial} erreur={erreurChargement} />
          )}
          {vue === "exercice-detail" && exerciceActifId && (
            <EcranExerciceDetail exerciceId={exerciceActifId} exercices={exercices} token={token} setVue={setVue} />
          )}
          {vue === "resultats" && (
            <EcranResultats resultats={resultats} chargement={chargementInitial} erreur={erreurChargement} />
          )}
        </>
      )}
    </div>
  );
}
