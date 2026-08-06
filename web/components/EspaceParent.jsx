"use client";

import React, { useState, useEffect } from "react";
import {
  GraduationCap, Lock, Mail, LogOut, Bell, Loader2, AlertTriangle,
  TrendingUp, CalendarX, Wallet, CalendarClock, ChevronDown, ScrollText,
  Check, User,
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
/*  Styles + palette — identiques aux autres espaces                   */
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
          <span className="eduai-display text-2xl" style={{ color: C.encre }}>Oskar<span style={{ color: C.accent }}>AI</span></span>
        </div>
        <div className="rounded-2xl p-8 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Espace Parent</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Connecte-toi pour suivre la scolarité de ton enfant.</p>
          <BandeauErreur message={erreurConnexion} />
          <form onSubmit={(e) => { e.preventDefault(); onConnexion(email, motDePasse); }} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}><Mail size={13} /> Adresse email</span>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="parent.dupont@test.cm"
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
/*  Barre de navigation + sélecteur d'enfant                            */
/* ------------------------------------------------------------------ */

function BarreNav({ vue, setVue, onDeconnexion }) {
  const items = [
    { id: "tableau-de-bord", label: "Tableau de bord" },
    { id: "bulletins", label: "Bulletins" },
    { id: "absences", label: "Absences" },
    { id: "paiements", label: "Paiements" },
    { id: "devoirs", label: "Devoirs" },
    { id: "notifications", label: "Notifications" },
  ];
  return (
    <div className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b flex-wrap gap-y-2"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}>
      <button onClick={() => setVue("tableau-de-bord")} className="eduai-focus flex items-center gap-2">
        <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
        <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>OskarAI</span>
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

function SelecteurEnfant({ enfants, enfantActif, setEnfantActif }) {
  const [ouvert, setOuvert] = useState(false);
  if (enfants.length <= 1) {
    const e = enfants[0];
    return e ? (
      <div className="flex items-center gap-2 mb-6" style={{ color: C.encreDoux }}>
        <User size={14} /><span className="text-sm">{e.nom} {e.prenom} · {e.classe}</span>
      </div>
    ) : null;
  }
  return (
    <div className="relative mb-6 inline-block">
      <button onClick={() => setOuvert((v) => !v)}
        className="eduai-focus flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium border"
        style={{ backgroundColor: C.surface, borderColor: C.ligne, color: C.encre }}>
        <User size={14} /> {enfantActif.nom} {enfantActif.prenom} · {enfantActif.classe}
        <ChevronDown size={14} color={C.encreAttenue} />
      </button>
      {ouvert && (
        <div className="absolute z-10 mt-1 rounded-lg border overflow-hidden" style={{ backgroundColor: C.surface, borderColor: C.ligne, boxShadow: C.surfaceOmbre, minWidth: "220px" }}>
          {enfants.map((e) => (
            <button key={e.eleve_id} onClick={() => { setEnfantActif(e); setOuvert(false); }}
              className="eduai-focus w-full text-left px-3.5 py-2.5 text-sm flex items-center justify-between"
              style={{ color: C.encre, backgroundColor: e.eleve_id === enfantActif.eleve_id ? C.bleuFond : "transparent" }}>
              <span>{e.nom} {e.prenom}</span>
              <span className="text-xs" style={{ color: C.encreDoux }}>{e.classe}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Tableau de bord de l'enfant                                 */
/* ------------------------------------------------------------------ */

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

function EcranTableauDeBord({ enfantId, token }) {
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/parent/enfants/${enfantId}/tableau-de-bord`, { token })
      .then(setDonnees).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [enfantId, token]);

  if (chargement) return <Chargement label="Chargement du tableau de bord..." />;
  if (erreur) return <BandeauErreur message={erreur} />;
  if (!donnees) return null;

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <CarteStat label="Moyenne générale" valeur={donnees.moyenne_generale === null ? "—" : `${donnees.moyenne_generale}/20`} icon={TrendingUp} />
        <CarteStat label="Absences" valeur={donnees.nombre_absences} icon={CalendarX} accent={donnees.nombre_absences > 0} />
        <CarteStat label="Retards" valeur={donnees.nombre_retards} icon={CalendarClock} />
      </div>

      <h2 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Dernières notes</h2>
      {donnees.dernieres_notes.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucune note enregistrée pour l'instant.</p>
      ) : (
        <div className="space-y-2.5">
          {donnees.dernieres_notes.map((n, i) => (
            <div key={i} className="rounded-xl px-5 py-3.5 flex items-center justify-between border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
              <div>
                <p className="text-sm font-medium" style={{ color: C.encre }}>{n.matiere}</p>
                <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{n.type} · {new Date(n.date).toLocaleDateString("fr-FR")}</p>
              </div>
              <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>{n.valeur}/{n.bareme}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Bulletins                                                   */
/* ------------------------------------------------------------------ */

function EcranBulletins({ enfantId, token }) {
  const [bulletins, setBulletins] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/parent/enfants/${enfantId}/bulletins`, { token })
      .then(setBulletins).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [enfantId, token]);

  if (chargement) return <Chargement />;
  return (
    <div>
      <BandeauErreur message={erreur} />
      {bulletins.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucun bulletin disponible pour l'instant.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {bulletins.map((b) => (
            <div key={b.trimestre} className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div className="flex items-center gap-2 mb-3">
                <ScrollText size={15} color={C.accentFonce} />
                <span className="text-sm font-semibold" style={{ color: C.encre }}>Trimestre {b.trimestre}</span>
              </div>
              <p className="eduai-display text-2xl mb-1" style={{ color: C.encre }}>
                {b.moyenne_generale === null ? "—" : `${b.moyenne_generale}/20`}
              </p>
              <p className="text-xs" style={{ color: C.encreDoux }}>
                {b.rang_classe ? `Rang : ${b.rang_classe}` : "Rang non disponible"}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Absences                                                    */
/* ------------------------------------------------------------------ */

function EcranAbsences({ enfantId, token }) {
  const [absences, setAbsences] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/parent/enfants/${enfantId}/absences`, { token })
      .then(setAbsences).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [enfantId, token]);

  if (chargement) return <Chargement />;
  return (
    <div>
      <BandeauErreur message={erreur} />
      {absences.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucune absence enregistrée.</p>
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          {absences.map((a, i) => (
            <div key={i} className="px-5 py-4 flex items-center justify-between" style={{ borderTop: i > 0 ? `1px solid ${C.ligne}` : "none" }}>
              <div>
                <p className="text-sm font-medium" style={{ color: C.encre }}>
                  {a.type_absence === "absence" ? "Absence" : "Retard"} — {new Date(a.date_absence).toLocaleDateString("fr-FR")}
                </p>
                {a.motif && <p className="text-xs mt-0.5 italic" style={{ color: C.encreAttenue }}>« {a.motif} »</p>}
              </div>
              <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: a.justifie ? C.vertFond : C.rougeFond, color: a.justifie ? C.vert : C.rouge }}>
                {a.justifie ? "Justifié" : "Non justifié"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Paiements                                                    */
/* ------------------------------------------------------------------ */

function EcranPaiements({ enfantId, token }) {
  const [paiements, setPaiements] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/parent/enfants/${enfantId}/paiements`, { token })
      .then(setPaiements).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [enfantId, token]);

  if (chargement) return <Chargement />;
  return (
    <div>
      <BandeauErreur message={erreur} />
      {paiements.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucun paiement enregistré.</p>
      ) : (
        <div className="space-y-3">
          {paiements.map((p, i) => {
            const restant = p.montant_du - p.montant_paye;
            return (
              <div key={i} className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium flex items-center gap-1.5" style={{ color: C.encre }}>
                    <Wallet size={14} color={C.accentFonce} /> {p.statut === "complet" ? "Payé intégralement" : p.statut === "partiel" ? "Paiement partiel" : "En attente"}
                  </span>
                  {p.statut === "complet" && <Check size={14} color={C.vert} />}
                </div>
                <div className="h-2 rounded-full overflow-hidden mb-2" style={{ backgroundColor: C.fond }}>
                  <div className="h-full rounded-full" style={{ width: `${(p.montant_paye / p.montant_du) * 100}%`, backgroundColor: restant > 0 ? C.ambre : C.vert }} />
                </div>
                <p className="eduai-mono text-xs" style={{ color: C.encreDoux }}>
                  {p.montant_paye.toLocaleString("fr-FR")} / {p.montant_du.toLocaleString("fr-FR")} FCFA
                  {restant > 0 && <span style={{ color: C.rouge }}> — reste {restant.toLocaleString("fr-FR")} FCFA</span>}
                </p>
                {p.date_echeance && <p className="text-[11px] mt-1" style={{ color: C.encreAttenue }}>Échéance : {new Date(p.date_echeance).toLocaleDateString("fr-FR")}</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Devoirs                                                     */
/* ------------------------------------------------------------------ */

function EcranDevoirs({ enfantId, token }) {
  const [devoirs, setDevoirs] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch(`/parent/enfants/${enfantId}/devoirs`, { token })
      .then(setDevoirs).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [enfantId, token]);

  if (chargement) return <Chargement />;
  return (
    <div>
      <BandeauErreur message={erreur} />
      {devoirs.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucun devoir à venir.</p>
      ) : (
        <div className="space-y-3">
          {devoirs.map((d, i) => (
            <div key={i} className="rounded-xl px-5 py-4 flex items-center justify-between border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
              <div>
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{d.titre}</p>
                <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{d.matiere}</p>
              </div>
              <span className="eduai-mono text-xs px-2.5 py-1 rounded-full" style={{ backgroundColor: C.ambreFond, color: C.ambre }}>
                {new Date(d.date_limite).toLocaleDateString("fr-FR")}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Notifications (propres au compte parent)                    */
/* ------------------------------------------------------------------ */

function EcranNotifications({ token }) {
  const [notifs, setNotifs] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    setChargement(true); setErreur(null);
    apiFetch("/parent/notifications", { token })
      .then(setNotifs).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  if (chargement) return <Chargement />;
  return (
    <div>
      <BandeauErreur message={erreur} />
      {notifs.length === 0 ? (
        <p className="text-sm" style={{ color: C.encreDoux }}>Aucune notification pour l'instant.</p>
      ) : (
        <div className="space-y-2.5">
          {notifs.map((n) => (
            <div key={n.id} className="rounded-xl px-5 py-4 border" style={{ backgroundColor: n.lue ? C.surface : C.bleuFond, borderColor: C.ligne }}>
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-semibold" style={{ color: C.encre }}>{n.titre}</p>
                {!n.lue && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: C.accent }} />}
              </div>
              <p className="text-xs" style={{ color: C.encreDoux }}>{n.message}</p>
              <p className="text-[11px] mt-1.5" style={{ color: C.encreAttenue }}>{new Date(n.created_at).toLocaleDateString("fr-FR")}</p>
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

export default function App() {
  const [token, setToken] = useState(null);
  const [connexionEnCours, setConnexionEnCours] = useState(false);
  const [erreurConnexion, setErreurConnexion] = useState(null);
  const [vue, setVue] = useState("tableau-de-bord");

  const [enfants, setEnfants] = useState([]);
  const [enfantActif, setEnfantActif] = useState(null);
  const [chargementEnfants, setChargementEnfants] = useState(true);
  const [erreurEnfants, setErreurEnfants] = useState(null);

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      setToken(access_token);
    } catch (e) { setErreurConnexion(e.message); }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() { setToken(null); setVue("tableau-de-bord"); setEnfants([]); setEnfantActif(null); }

  useEffect(() => {
    if (!token) return;
    setChargementEnfants(true);
    apiFetch("/parent/enfants", { token })
      .then((d) => { setEnfants(d); if (d.length) setEnfantActif(d[0]); })
      .catch((e) => {
        if (e.status === 401) { setToken(null); setErreurConnexion("Ce compte n'a pas accès à cet espace."); }
        else setErreurEnfants(e.message);
      })
      .finally(() => setChargementEnfants(false));
  }, [token]);

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      {!token ? (
        <EcranConnexion onConnexion={connecter} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} />
          <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
            <h1 className="eduai-display text-3xl mb-1" style={{ color: C.encre }}>
              {vue === "notifications" ? "Notifications" : "Suivi scolaire"}
            </h1>

            {chargementEnfants ? <Chargement label="Chargement de vos enfants..." /> : (
              <>
                <BandeauErreur message={erreurEnfants} />
                {enfants.length === 0 && !erreurEnfants ? (
                  <p className="text-sm mt-4" style={{ color: C.encreDoux }}>Aucun enfant lié à ce compte pour l'instant.</p>
                ) : (
                  <>
                    {vue !== "notifications" && enfantActif && (
                      <div className="mt-6">
                        <SelecteurEnfant enfants={enfants} enfantActif={enfantActif} setEnfantActif={setEnfantActif} />
                      </div>
                    )}
                    <div className="mt-2">
                      {vue === "tableau-de-bord" && enfantActif && <EcranTableauDeBord enfantId={enfantActif.eleve_id} token={token} />}
                      {vue === "bulletins" && enfantActif && <EcranBulletins enfantId={enfantActif.eleve_id} token={token} />}
                      {vue === "absences" && enfantActif && <EcranAbsences enfantId={enfantActif.eleve_id} token={token} />}
                      {vue === "paiements" && enfantActif && <EcranPaiements enfantId={enfantActif.eleve_id} token={token} />}
                      {vue === "devoirs" && enfantActif && <EcranDevoirs enfantId={enfantActif.eleve_id} token={token} />}
                      {vue === "notifications" && <EcranNotifications token={token} />}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
