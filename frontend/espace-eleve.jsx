import React, { useState } from "react";
import {
  BookOpen, Calculator, FlaskConical, Leaf, Landmark, Languages,
  ChevronRight, ChevronLeft, LogOut, Bell, TrendingUp, CalendarClock,
  Check, X as XIcon, Sparkles, GraduationCap, Lock, Mail,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Données de démonstration — reprises des exercices réellement      */
/*  générés et testés plus tôt (pipeline maths / physique-chimie).    */
/* ------------------------------------------------------------------ */

const ELEVE = { prenom: "Jean", nom: "Dupont", classe: "6ème A", etablissement: "Lycée de Mbankomo" };

const MATIERES = [
  { nom: "Mathématiques", icon: Calculator, papier: "grille" },
  { nom: "Physique-Chimie", icon: FlaskConical, papier: "grille" },
  { nom: "Français", icon: Languages, papier: "lignes" },
  { nom: "SVT", icon: Leaf, papier: "lignes" },
  { nom: "Histoire-Géographie", icon: Landmark, papier: "lignes" },
];

const EXERCICES = [
  { id: 1, matiere: "Mathématiques", theme: "Nombres entiers", difficulte: "facile",
    enonce: "Un pêcheur de Douala ramène 9 356 kg de poisson. Écris ce nombre en toutes lettres.",
    corrige: "Neuf mille trois cent cinquante-six.",
    etapes: ["Décomposer 9356 en milliers, centaines, dizaines et unités.", "Lire chaque groupe : neuf mille trois cent cinquante-six."] },
  { id: 2, matiere: "Mathématiques", theme: "Équations", difficulte: "moyen",
    enonce: "Résous l'équation suivante : 7x + 21 = 105",
    corrige: "x = 12",
    etapes: ["7x + 21 = 105", "7x = 105 − 21 = 84", "x = 84 / 7 = 12"] },
  { id: 3, matiere: "Mathématiques", theme: "Géométrie", difficulte: "facile",
    enonce: "Un champ rectangulaire à Bafia mesure 14 m de long sur 4 m de large. Calcule son aire.",
    corrige: "56 m²",
    etapes: ["Aire du rectangle = longueur × largeur", "Aire = 14 × 4 = 56 m²"] },
  { id: 4, matiere: "Physique-Chimie", theme: "Mécanique", difficulte: "facile",
    enonce: "Un bus effectue le trajet Douala–Yaoundé de 280 km en 4 h. Calcule sa vitesse moyenne.",
    corrige: "70 km/h",
    etapes: ["Vitesse moyenne = distance / temps", "v = 280 / 4 = 70 km/h"] },
  { id: 5, matiere: "Physique-Chimie", theme: "Électricité", difficulte: "moyen",
    enonce: "Un conducteur ohmique de résistance 40 Ω est parcouru par un courant d'intensité 3 A. Calcule la tension à ses bornes.",
    corrige: "120 V",
    etapes: ["Loi d'Ohm : U = R × I", "U = 40 × 3 = 120 V"] },
  { id: 6, matiere: "Français", theme: "Accords sujet-verbe", difficulte: "facile",
    enonce: "Corrige la phrase suivante : « Les enfants joue au football. »",
    corrige: "Les enfants jouent au football.",
    etapes: ["Le verbe s'accorde avec son sujet en nombre et en personne.", "« Les enfants » est pluriel → « jouent »."] },
  { id: 7, matiere: "SVT", theme: "La cellule, unité du vivant", difficulte: "moyen",
    enonce: "Explique en une phrase le rôle du noyau dans une cellule végétale.",
    corrige: "Le noyau contient l'information génétique et dirige les activités de la cellule.",
    etapes: ["Identifier les organites principaux de la cellule.", "Relier chaque organite à sa fonction."] },
  { id: 8, matiere: "Histoire-Géographie", theme: "Le Cameroun précolonial", difficulte: "moyen",
    enonce: "Cite deux royaumes ou chefferies présents sur le territoire camerounais avant la colonisation.",
    corrige: "Le royaume Bamoun et le royaume Bamiléké, entre autres.",
    etapes: ["Repérer les grandes zones culturelles précoloniales du Cameroun.", "Nommer un exemple représentatif par zone."] },
];

const RESULTATS = [
  { matiere: "Mathématiques", moyenne: 14.5 },
  { matiere: "Physique-Chimie", moyenne: 12.8 },
  { matiere: "Français", moyenne: 15.2 },
  { matiere: "SVT", moyenne: 13.0 },
  { matiere: "Histoire-Géographie", moyenne: 11.5 },
];

const DEVOIRS = [
  { titre: "Exercices sur les nombres entiers", matiere: "Mathématiques", date: "15 septembre" },
  { titre: "Rédaction : un souvenir de vacances", matiere: "Français", date: "18 septembre" },
];

const DIFFICULTE_LABEL = { facile: "Facile", moyen: "Moyen", difficile: "Difficile" };

/* ------------------------------------------------------------------ */
/*  Styles injectés — polices, textures de papier, animation tampon   */
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

  .eduai-stamp {
    animation: eduai-stamp-in 420ms cubic-bezier(0.2, 1.4, 0.4, 1) forwards;
  }
  @keyframes eduai-stamp-in {
    0%   { opacity: 0; transform: scale(1.6) rotate(-14deg); }
    60%  { opacity: 1; transform: scale(0.95) rotate(-5deg); }
    100% { opacity: 1; transform: scale(1) rotate(-6deg); }
  }

  .eduai-fade-in { animation: eduai-fade 320ms ease-out forwards; }
  @keyframes eduai-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  @media (prefers-reduced-motion: reduce) {
    .eduai-stamp, .eduai-fade-in { animation: none !important; }
  }

  .eduai-focus:focus-visible {
    outline: 2px solid #B08D57;
    outline-offset: 2px;
    border-radius: 6px;
  }
`;

/* ------------------------------------------------------------------ */
/*  Palette v2 — claire et raffinée (retour : la v1 "ardoise" sombre  */
/*  manquait d'élégance). Fond porcelaine clair, encre bleu-nuit pour  */
/*  le texte, accent laiton plutôt que terracotta, rouge-correction    */
/*  réservé au tampon du corrigé — jamais dominant.                    */
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
};

function badgeColorForDifficulte(d) {
  if (d === "facile") return { bg: C.vertFond, fg: C.vert };
  if (d === "moyen") return { bg: C.ambreFond, fg: C.ambre };
  return { bg: C.rougeFond, fg: C.rouge };
}

/* ------------------------------------------------------------------ */
/*  Écran : Connexion                                                  */
/* ------------------------------------------------------------------ */

function EcranConnexion({ onConnexion }) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");

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
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Content de te revoir</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Connecte-toi pour retrouver tes exercices.</p>

          <form onSubmit={(e) => { e.preventDefault(); onConnexion(); }} className="space-y-4">
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
              type="submit"
              className="eduai-focus w-full rounded-lg py-2.5 text-sm font-semibold mt-2 transition-colors"
              style={{ backgroundColor: C.encre, color: C.surface }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#2E3F60")}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = C.encre)}
            >
              Se connecter
            </button>
          </form>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: C.encreAttenue }}>
          Un souci de connexion ? Demande à ton enseignant.
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Barre de navigation                                                */
/* ------------------------------------------------------------------ */

function BarreNav({ vue, setVue, onDeconnexion }) {
  const items = [
    { id: "accueil", label: "Accueil" },
    { id: "exercices", label: "Exercices" },
    { id: "resultats", label: "Résultats" },
  ];
  return (
    <div
      className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}
    >
      <button onClick={() => setVue("accueil")} className="eduai-focus flex items-center gap-2">
        <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
        <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>ÉduAI Afrique</span>
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
            {vue === it.id && (
              <span className="absolute left-0 right-0 -bottom-[15px] h-[2px]" style={{ backgroundColor: C.accent }} />
            )}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-4">
        <button className="eduai-focus relative" aria-label="Notifications">
          <Bell size={17} color={C.encreDoux} />
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full" style={{ backgroundColor: C.accent }} />
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
/*  Écran : Accueil                                                    */
/* ------------------------------------------------------------------ */

function EcranAccueil({ setVue }) {
  const moyenneGenerale = (RESULTATS.reduce((s, r) => s + r.moyenne, 0) / RESULTATS.length).toFixed(1);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <p className="eduai-mono text-xs uppercase tracking-wider mb-1" style={{ color: C.encreAttenue }}>
        {ELEVE.classe} · {ELEVE.etablissement}
      </p>
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Bonjour, {ELEVE.prenom}</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <CarteStat label="Moyenne générale" valeur={`${moyenneGenerale}/20`} icon={TrendingUp} />
        <CarteStat label="Exercices disponibles" valeur={EXERCICES.length} icon={BookOpen} />
        <CarteStat label="Devoirs à venir" valeur={DEVOIRS.length} icon={CalendarClock} />
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="eduai-display text-lg" style={{ color: C.encre }}>À rendre prochainement</h2>
        <button onClick={() => setVue("exercices")} className="eduai-focus text-xs font-medium flex items-center gap-1" style={{ color: C.accentFonce }}>
          Voir tous les exercices <ChevronRight size={14} />
        </button>
      </div>

      <div className="space-y-3">
        {DEVOIRS.map((d, i) => (
          <div key={i} className="rounded-xl px-5 py-4 flex items-center justify-between border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
            <div>
              <p className="text-sm font-semibold" style={{ color: C.encre }}>{d.titre}</p>
              <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{d.matiere}</p>
            </div>
            <div className="eduai-mono text-xs px-2.5 py-1 rounded-full" style={{ backgroundColor: C.ambreFond, color: C.ambre }}>
              {d.date}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CarteStat({ label, valeur, icon: Icon }) {
  return (
    <div className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
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

function EcranExercices({ setVue, setExerciceActifId, filtre, setFiltre }) {
  const exercicesFiltres = filtre ? EXERCICES.filter((e) => e.matiere === filtre) : EXERCICES;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-6" style={{ color: C.encre }}>Exercices</h1>

      <div className="flex gap-2 mb-8 overflow-x-auto pb-1">
        <ChipMatiere label="Toutes" active={!filtre} onClick={() => setFiltre(null)} />
        {MATIERES.map((m) => (
          <ChipMatiere key={m.nom} label={m.nom} active={filtre === m.nom} onClick={() => setFiltre(m.nom)} icon={m.icon} />
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {exercicesFiltres.map((ex) => {
          const matiereInfo = MATIERES.find((m) => m.nom === ex.matiere);
          const badge = badgeColorForDifficulte(ex.difficulte);
          const Icon = matiereInfo?.icon || BookOpen;
          return (
            <button
              key={ex.id}
              onClick={() => { setExerciceActifId(ex.id); setVue("exercice-detail"); }}
              className={`eduai-focus text-left rounded-xl p-5 border eduai-paper-${matiereInfo?.papier || "lignes"} transition-transform hover:-translate-y-0.5`}
              style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `3px solid ${C.accent}` }}
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
      </div>
    </div>
  );
}

function ChipMatiere({ label, active, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className="eduai-focus flex items-center gap-1.5 whitespace-nowrap px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors border"
      style={{
        backgroundColor: active ? C.encre : C.surface,
        color: active ? C.surface : C.encreDoux,
        borderColor: active ? C.encre : C.ligne,
      }}
    >
      {Icon && <Icon size={13} />}
      {label}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Détail d'un exercice                                       */
/* ------------------------------------------------------------------ */

function EcranExerciceDetail({ exerciceId, setVue, tentatives, setTentatives }) {
  const [revele, setRevele] = useState(false);
  const ex = EXERCICES.find((e) => e.id === exerciceId);
  const matiereInfo = MATIERES.find((m) => m.nom === ex.matiere);
  const badge = badgeColorForDifficulte(ex.difficulte);
  const tentative = tentatives[exerciceId];

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <button onClick={() => setVue("exercices")} className="eduai-focus flex items-center gap-1 text-xs font-medium mb-6" style={{ color: C.encreAttenue }}>
        <ChevronLeft size={14} /> Retour aux exercices
      </button>

      <div
        className={`rounded-2xl p-7 border eduai-paper-${matiereInfo?.papier || "lignes"}`}
        style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne, borderLeft: `4px solid ${C.accent}` }}
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-semibold" style={{ color: C.accentFonce }}>{ex.matiere}</span>
          <span style={{ color: C.ligne }}>·</span>
          <span className="text-xs" style={{ color: C.encreDoux }}>{ex.theme}</span>
          <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full ml-auto" style={{ backgroundColor: badge.bg, color: badge.fg }}>
            {DIFFICULTE_LABEL[ex.difficulte]}
          </span>
        </div>

        <p className="eduai-display text-lg leading-relaxed mb-8" style={{ color: C.encre }}>{ex.enonce}</p>

        {!revele && (
          <button
            onClick={() => setRevele(true)}
            className="eduai-focus flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors"
            style={{ backgroundColor: C.encre, color: C.surface }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#2E3F60")}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = C.encre)}
          >
            <Sparkles size={15} /> Révéler le corrigé
          </button>
        )}

        {revele && (
          <div className="eduai-stamp">
            <div className="rounded-xl p-5 mb-5 relative" style={{ backgroundColor: C.fond, border: `1.5px dashed ${C.rouge}` }}>
              <span
                className="eduai-mono text-[10px] font-bold px-2 py-0.5 rounded absolute -top-3 left-4"
                style={{ backgroundColor: C.surface, color: C.rouge, border: `1.5px solid ${C.rouge}` }}
              >
                CORRIGÉ
              </span>
              <p className="text-base font-semibold mt-1.5 mb-4" style={{ color: C.rouge }}>{ex.corrige}</p>
              <ol className="space-y-1.5">
                {ex.etapes.map((etape, i) => (
                  <li key={i} className="text-sm flex gap-2" style={{ color: C.encreDoux }}>
                    <span className="eduai-mono" style={{ color: C.accentClair }}>{i + 1}.</span>
                    {etape}
                  </li>
                ))}
              </ol>
            </div>

            {tentative === undefined ? (
              <div>
                <p className="text-xs font-medium mb-2.5" style={{ color: C.encreDoux }}>As-tu trouvé la bonne réponse ?</p>
                <div className="flex gap-2.5">
                  <button
                    onClick={() => setTentatives({ ...tentatives, [exerciceId]: true })}
                    className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                    style={{ backgroundColor: C.vertFond, color: C.vert }}
                  >
                    <Check size={15} /> Oui, réussi
                  </button>
                  <button
                    onClick={() => setTentatives({ ...tentatives, [exerciceId]: false })}
                    className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                    style={{ backgroundColor: C.rougeFond, color: C.rouge }}
                  >
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
/*  Écran : Résultats                                                  */
/* ------------------------------------------------------------------ */

function EcranResultats() {
  const max = 20;
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Mes résultats</h1>

      <div className="rounded-2xl p-7 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <div className="space-y-5">
          {RESULTATS.map((r) => (
            <div key={r.matiere}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-medium" style={{ color: C.encre }}>{r.matiere}</span>
                <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>{r.moyenne.toFixed(1)}/20</span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: C.fond }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${(r.moyenne / max) * 100}%`, backgroundColor: r.moyenne >= 12 ? C.vert : C.ambre }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Application                                                        */
/* ------------------------------------------------------------------ */

export default function App() {
  const [connecte, setConnecte] = useState(false);
  const [vue, setVue] = useState("accueil");
  const [filtre, setFiltre] = useState(null);
  const [exerciceActifId, setExerciceActifId] = useState(null);
  const [tentatives, setTentatives] = useState({});

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>

      {!connecte ? (
        <EcranConnexion onConnexion={() => setConnecte(true)} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={() => setConnecte(false)} />
          {vue === "accueil" && <EcranAccueil setVue={setVue} />}
          {vue === "exercices" && (
            <EcranExercices setVue={setVue} setExerciceActifId={setExerciceActifId} filtre={filtre} setFiltre={setFiltre} />
          )}
          {vue === "exercice-detail" && exerciceActifId && (
            <EcranExerciceDetail exerciceId={exerciceActifId} setVue={setVue} tentatives={tentatives} setTentatives={setTentatives} />
          )}
          {vue === "resultats" && <EcranResultats />}
        </>
      )}
    </div>
  );
}
