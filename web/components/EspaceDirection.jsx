"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GraduationCap, Lock, Mail, LogOut, Bell, Loader2, AlertTriangle,
  Users, GraduationCap as CapIcon, School, TrendingUp, Wallet,
  ClipboardList, UserCheck, BarChart3, CalendarClock, Check, X as XIcon,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Configuration API — identique au pattern établi côté Enseignant   */
/* ------------------------------------------------------------------ */

const API_BASE_URL = "http://89.116.111.3:8000";

class ErreurApi extends Error {}

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
    throw new ErreurApi(typeof message === "string" ? message : JSON.stringify(message));
  }
  return donnees;
}

/* ------------------------------------------------------------------ */
/*  Styles + palette — identiques aux espaces Élève / Enseignant       */
/* ------------------------------------------------------------------ */

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
  .eduai-root { font-family: 'IBM Plex Sans', sans-serif; }
  .eduai-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; }
  .eduai-mono { font-family: 'Space Mono', monospace; letter-spacing: 0.02em; }
  .eduai-fade-in { animation: eduai-fade 320ms ease-out forwards; }
  @keyframes eduai-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  .eduai-spin { animation: eduai-spin 1.1s linear infinite; }
  @keyframes eduai-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .eduai-fade-in { animation: none !important; } .eduai-spin { animation-duration: 2.4s; } }
  .eduai-focus:focus-visible { outline: 2px solid #B08D57; outline-offset: 2px; border-radius: 6px; }
`;

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
          <span className="eduai-display text-2xl" style={{ color: C.encre }}>ÉduAI <span style={{ color: C.accent }}>Afrique</span></span>
        </div>
        <div className="rounded-2xl p-8 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Espace Direction</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Connecte-toi pour piloter ton établissement.</p>
          <BandeauErreur message={erreurConnexion} />
          <form onSubmit={(e) => { e.preventDefault(); onConnexion(email, motDePasse); }} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}><Mail size={13} /> Adresse email</span>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="directeur@ecole.cm"
                className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            </label>
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}><Lock size={13} /> Mot de passe</span>
              <input type="password" required value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} placeholder="••••••••"
                className="eduai-focus w-full rounded-lg px-3.5 py-2.5 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            </label>
            <button type="submit" disabled={connexionEnCours}
              className="eduai-focus w-full flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold mt-2 transition-colors disabled:opacity-60"
              style={{ backgroundColor: C.encre, color: C.surface }}>
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
/*  Barre de navigation                                                */
/* ------------------------------------------------------------------ */

function BarreNav({ vue, setVue, onDeconnexion }) {
  const items = [
    { id: "tableau-de-bord", label: "Tableau de bord" },
    { id: "validations", label: "Validations" },
    { id: "enseignants", label: "Enseignants" },
    { id: "classes", label: "Classes" },
    { id: "paiements", label: "Paiements" },
  ];
  return (
    <div className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b flex-wrap gap-y-2"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}>
      <button onClick={() => setVue("tableau-de-bord")} className="eduai-focus flex items-center gap-2">
        <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
        <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>ÉduAI Afrique</span>
      </button>
      <nav className="flex items-center gap-4 overflow-x-auto">
        {items.map((it) => (
          <button key={it.id} onClick={() => setVue(it.id)}
            className="eduai-focus relative pb-1 text-xs font-medium transition-colors whitespace-nowrap"
            style={{ color: vue === it.id ? C.encre : C.encreAttenue }}>
            {it.label}
            {vue === it.id && <span className="absolute left-0 right-0 -bottom-[15px] h-[2px]" style={{ backgroundColor: C.accent }} />}
          </button>
        ))}
      </nav>
      <div className="flex items-center gap-4">
        <button className="eduai-focus relative" aria-label="Notifications"><Bell size={17} color={C.encreDoux} /></button>
        <button onClick={onDeconnexion} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.encreDoux }}>
          <LogOut size={14} /><span className="hidden sm:inline">Déconnexion</span>
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Tableau de bord                                             */
/* ------------------------------------------------------------------ */

function CarteStat({ label, valeur, icon: Icon, accent, sousTexte }) {
  return (
    <div className="rounded-xl p-5 border" style={{ backgroundColor: accent ? C.encre : C.surface, boxShadow: C.surfaceOmbre, borderColor: accent ? C.encre : C.ligne }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: accent ? "rgba(255,255,255,0.75)" : C.encreDoux }}>{label}</span>
        <Icon size={15} color={accent ? C.accentClair : C.encreAttenue} />
      </div>
      <p className="eduai-display text-2xl" style={{ color: accent ? C.surface : C.encre }}>{valeur}</p>
      {sousTexte && <p className="text-[11px] mt-1" style={{ color: accent ? "rgba(255,255,255,0.55)" : C.encreAttenue }}>{sousTexte}</p>}
    </div>
  );
}

function EcranTableauDeBord({ token, setVue }) {
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/direction/tableau-de-bord", { token })
      .then(setDonnees).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  if (chargement) return <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10"><Chargement label="Chargement du tableau de bord..." /></div>;
  if (erreur) return <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10"><BandeauErreur message={erreur} /></div>;
  if (!donnees) return null;

  const tauxPaiement = donnees.montant_du_total > 0 ? (donnees.montant_paye_total / donnees.montant_du_total) * 100 : 100;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Tableau de bord</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>Vue d'ensemble de l'établissement.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <CarteStat label="Élèves" valeur={donnees.effectif_eleves} icon={Users} />
        <CarteStat label="Enseignants" valeur={donnees.effectif_enseignants} icon={CapIcon} />
        <CarteStat label="Classes" valeur={donnees.nombre_classes} icon={School} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <CarteStat
          label="Moyenne générale" icon={TrendingUp}
          valeur={donnees.moyenne_generale_etablissement === null ? "—" : `${donnees.moyenne_generale_etablissement}/20`}
        />
        <CarteStat
          label="Taux de réussite (auto-évaluations)" icon={BarChart3}
          valeur={donnees.taux_reussite_tentatives_pct === null ? "—" : `${donnees.taux_reussite_tentatives_pct}%`}
        />
        <CarteStat
          label="Exercices en attente" icon={ClipboardList} accent
          valeur={donnees.exercices_en_attente_validation}
          sousTexte="Bibliothèque commune, votre périmètre"
        />
      </div>

      <div className="rounded-xl p-5 border mb-4" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium flex items-center gap-1.5" style={{ color: C.encre }}><Wallet size={15} color={C.accentFonce} /> Paiements</span>
          <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>
            {donnees.montant_paye_total.toLocaleString("fr-FR")} / {donnees.montant_du_total.toLocaleString("fr-FR")} FCFA
          </span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: C.fond }}>
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${tauxPaiement}%`, backgroundColor: tauxPaiement >= 80 ? C.vert : C.ambre }} />
        </div>
        <button onClick={() => setVue("paiements")} className="eduai-focus text-xs font-medium mt-3" style={{ color: C.accentFonce }}>
          Voir les retards →
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Validations en attente par matière/niveau                  */
/* ------------------------------------------------------------------ */

function EcranValidations({ token }) {
  const [lignes, setLignes] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/direction/validations-en-attente", { token })
      .then(setLignes).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  const total = lignes.reduce((s, l) => s + l.nombre_en_attente, 0);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Validations en attente</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        {total} exercice{total !== 1 ? "s" : ""} de la bibliothèque commune en attente, dans les matières/niveaux enseignés ici.
      </p>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : lignes.length === 0 ? (
        <div className="rounded-xl p-8 text-center border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
          <p className="text-sm" style={{ color: C.encreDoux }}>Rien en attente pour l'instant.</p>
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          {lignes.map((l, i) => (
            <div key={i} className="px-5 py-4 flex items-center justify-between" style={{ borderTop: i > 0 ? `1px solid ${C.ligne}` : "none" }}>
              <div>
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{l.matiere}</p>
                <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{l.niveau}</p>
              </div>
              <span className="eduai-mono text-sm font-bold px-3 py-1 rounded-full" style={{ backgroundColor: C.ambreFond, color: C.ambre }}>
                {l.nombre_en_attente}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Activité des enseignants                                   */
/* ------------------------------------------------------------------ */

function EcranEnseignants({ token }) {
  const [lignes, setLignes] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/direction/enseignants/activite", { token })
      .then(setLignes).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Activité des enseignants</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>Qui valide, qui rejette, dans la bibliothèque commune.</p>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : (
        <div className="space-y-3">
          {lignes.map((e, i) => (
            <div key={i} className="rounded-xl p-5 border flex items-center justify-between" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ backgroundColor: C.bleuFond }}>
                  <UserCheck size={15} color={C.encre} />
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: C.encre }}>{e.enseignant}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{e.email} · {e.nombre_classes_affectees} classe{e.nombre_classes_affectees !== 1 ? "s" : ""}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="eduai-mono text-xs px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: C.vertFond, color: C.vert }}>
                  <Check size={10} /> {e.nombre_exercices_valides}
                </span>
                <span className="eduai-mono text-xs px-2 py-0.5 rounded-full flex items-center gap-1" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                  <XIcon size={10} /> {e.nombre_exercices_rejetes}
                </span>
              </div>
            </div>
          ))}
          {lignes.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun enseignant actif trouvé.</p>}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Moyennes par classe                                         */
/* ------------------------------------------------------------------ */

function EcranClasses({ token }) {
  const [lignes, setLignes] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/direction/classes/moyennes", { token })
      .then(setLignes).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Moyennes par classe</h1>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : (
        <div className="rounded-2xl p-7 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          <div className="space-y-5">
            {lignes.map((l, i) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium" style={{ color: C.encre }}>{l.classe} · {l.matiere}</span>
                  <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>{l.moyenne_sur_20}/20</span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: C.fond }}>
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${(l.moyenne_sur_20 / 20) * 100}%`, backgroundColor: l.moyenne_sur_20 >= 12 ? C.vert : C.ambre }} />
                </div>
                <p className="text-[11px] mt-1" style={{ color: C.encreAttenue }}>{l.effectif_note} note{l.effectif_note !== 1 ? "s" : ""}</p>
              </div>
            ))}
            {lignes.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucune note enregistrée pour l'instant.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Paiements en retard                                         */
/* ------------------------------------------------------------------ */

function EcranPaiements({ token }) {
  const [lignes, setLignes] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/direction/paiements/retards", { token })
      .then(setLignes).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Paiements en retard</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>{lignes.length} élève{lignes.length !== 1 ? "s" : ""} avec un paiement en retard.</p>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : lignes.length === 0 ? (
        <div className="rounded-xl p-8 text-center border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
          <p className="text-sm" style={{ color: C.encreDoux }}>Aucun retard — tout est à jour.</p>
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          {lignes.map((p, i) => (
            <div key={i} className="px-5 py-4 flex items-center justify-between" style={{ borderTop: i > 0 ? `1px solid ${C.ligne}` : "none" }}>
              <div className="flex items-center gap-3">
                <CalendarClock size={16} color={C.rouge} />
                <div>
                  <p className="text-sm font-semibold" style={{ color: C.encre }}>{p.eleve_nom} {p.eleve_prenom}</p>
                  <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{p.classe} · échéance {p.date_echeance ? new Date(p.date_echeance).toLocaleDateString("fr-FR") : "—"}</p>
                </div>
              </div>
              <span className="eduai-mono text-sm font-bold" style={{ color: C.rouge }}>
                {p.montant_restant.toLocaleString("fr-FR")} FCFA
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Application                                                        */
/* ------------------------------------------------------------------ */

export default function EspaceDirection() {
  const [token, setToken] = useState(null);
  const [connexionEnCours, setConnexionEnCours] = useState(false);
  const [erreurConnexion, setErreurConnexion] = useState(null);
  const [vue, setVue] = useState("tableau-de-bord");

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      setToken(access_token);
    } catch (e) { setErreurConnexion(e.message); }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() { setToken(null); setVue("tableau-de-bord"); }

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      {!token ? (
        <EcranConnexion onConnexion={connecter} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} />
          {vue === "tableau-de-bord" && <EcranTableauDeBord token={token} setVue={setVue} />}
          {vue === "validations" && <EcranValidations token={token} />}
          {vue === "enseignants" && <EcranEnseignants token={token} />}
          {vue === "classes" && <EcranClasses token={token} />}
          {vue === "paiements" && <EcranPaiements token={token} />}
        </>
      )}
    </div>
  );
}
