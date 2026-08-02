"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GraduationCap, Lock, Mail, LogOut, Loader2, AlertTriangle, Check,
  Plus, Upload, FileText, Trash2, Building2, Power, Copy, BookMarked,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Configuration API                                                  */
/* ------------------------------------------------------------------ */

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
      headers: {
        ...(body && !estFormData ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? (estFormData ? body : JSON.stringify(body)) : undefined,
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
/*  Styles + palette (identiques au reste de la plateforme)            */
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
function BandeauSucces({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-lg px-4 py-3 mb-4 flex items-start gap-2 text-sm" style={{ backgroundColor: C.vertFond, color: C.vert }}>
      <Check size={15} className="mt-0.5 flex-shrink-0" /><span>{message}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Connexion                                                           */
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
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Admin Plateforme</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Supervision de tous les établissements de la plateforme.</p>
          <BandeauErreur message={erreurConnexion} />
          <form onSubmit={(e) => { e.preventDefault(); onConnexion(email, motDePasse); }} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}><Mail size={13} /> Adresse email</span>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="plateforme@eduai.africa"
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
/*  Navigation                                                          */
/* ------------------------------------------------------------------ */

function BarreNav({ vue, setVue, onDeconnexion }) {
  const items = [
    { id: "etablissements", label: "Établissements" },
    { id: "documents", label: "Documents" },
    { id: "bibliotheque", label: "Bibliothèque commune" },
  ];
  return (
    <div className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b flex-wrap gap-y-2"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}>
      <div className="flex items-center gap-2">
        <GraduationCap size={20} color={C.encre} strokeWidth={1.75} />
        <span className="eduai-display text-base hidden sm:inline" style={{ color: C.encre }}>ÉduAI Afrique</span>
        <span className="text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 ml-1" style={{ backgroundColor: C.bleuFond, color: C.encre }}>Plateforme</span>
      </div>
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
      <button onClick={onDeconnexion} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.encreDoux }}>
        <LogOut size={14} /><span className="hidden sm:inline">Déconnexion</span>
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Établissements                                              */
/* ------------------------------------------------------------------ */

function FormulaireCreationEtablissement({ token, onCree }) {
  const [ouvert, setOuvert] = useState(false);
  const [nom, setNom] = useState("");
  const [pays, setPays] = useState("Cameroun");
  const [ville, setVille] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminNom, setAdminNom] = useState("");
  const [adminPrenom, setAdminPrenom] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null);
    try {
      const resultat = await apiFetch("/plateforme/etablissements", {
        method: "POST", token,
        body: { nom, pays, ville: ville || null, admin_email: adminEmail, admin_nom: adminNom, admin_prenom: adminPrenom },
      });
      setNom(""); setVille(""); setAdminEmail(""); setAdminNom(""); setAdminPrenom(""); setOuvert(false);
      onCree(resultat);
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  if (!ouvert) {
    return (
      <button onClick={() => setOuvert(true)} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.accentFonce }}>
        <Plus size={13} /> Créer un établissement
      </button>
    );
  }

  return (
    <form onSubmit={soumettre} className="rounded-lg p-4 border space-y-2.5" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
      <BandeauErreur message={erreur} />
      <p className="text-xs font-semibold" style={{ color: C.encre }}>Informations de l'établissement</p>
      <div className="grid grid-cols-2 gap-2">
        <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom de l'établissement"
          className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
        <input required value={pays} onChange={(e) => setPays(e.target.value)} placeholder="Pays"
          className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
      </div>
      <input value={ville} onChange={(e) => setVille(e.target.value)} placeholder="Ville (optionnel)"
        className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />

      <p className="text-xs font-semibold pt-2" style={{ color: C.encre }}>Premier compte administratif</p>
      <input required type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} placeholder="Email du responsable"
        className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
      <div className="grid grid-cols-2 gap-2">
        <input required value={adminNom} onChange={(e) => setAdminNom(e.target.value)} placeholder="Nom"
          className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
        <input required value={adminPrenom} onChange={(e) => setAdminPrenom(e.target.value)} placeholder="Prénom"
          className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
      </div>

      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={envoi} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {envoi ? <Loader2 size={12} className="eduai-spin" /> : "Créer"}
        </button>
        <button type="button" onClick={() => setOuvert(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
      </div>
    </form>
  );
}

function BandeauCompteCree({ compte, onFerme }) {
  const [copie, setCopie] = useState(false);
  if (!compte) return null;
  function copier() {
    navigator.clipboard?.writeText(`${compte.email} / ${compte.mot_de_passe_provisoire}`);
    setCopie(true); setTimeout(() => setCopie(false), 1500);
  }
  return (
    <div className="rounded-lg px-4 py-3 mb-4 text-sm" style={{ backgroundColor: C.vertFond, color: C.vert }}>
      <p className="font-semibold mb-1">Établissement créé — identifiants du premier compte (à transmettre une seule fois) :</p>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="eduai-mono text-xs">{compte.email} / {compte.mot_de_passe_provisoire}</span>
        <button onClick={copier} className="eduai-focus flex items-center gap-1 text-xs font-medium underline">
          <Copy size={11} /> {copie ? "Copié !" : "Copier"}
        </button>
        <button onClick={onFerme} className="eduai-focus text-xs underline ml-auto">Fermer</button>
      </div>
    </div>
  );
}

function EcranEtablissements({ token }) {
  const [etablissements, setEtablissements] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [compteCree, setCompteCree] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/plateforme/etablissements", { token })
      .then(setEtablissements).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function basculerActif(etab) {
    try {
      await apiFetch(`/plateforme/etablissements/${etab.id}/${etab.actif ? "desactiver" : "reactiver"}`, { method: "PATCH", token });
      charger();
    } catch (e) { setErreur(e.message); }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Établissements</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>Toutes les écoles clientes de la plateforme.</p>

      <BandeauErreur message={erreur} />
      <BandeauCompteCree compte={compteCree} onFerme={() => setCompteCree(null)} />

      <div className="rounded-2xl p-6 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <FormulaireCreationEtablissement token={token} onCree={(r) => { setCompteCree(r.compte_admin); charger(); }} />

        {chargement ? <Chargement /> : (
          <div className="space-y-2 mt-5">
            {etablissements.map((e) => (
              <div key={e.id} className="flex items-center justify-between rounded-lg border px-3 py-2.5" style={{ borderColor: C.ligne }}>
                <div className="flex items-center gap-2.5 min-w-0">
                  <Building2 size={15} color={C.encreAttenue} className="flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: C.encre }}>{e.nom}</p>
                    <p className="text-xs" style={{ color: C.encreAttenue }}>
                      {[e.ville, e.pays].filter(Boolean).join(", ")} · {e.nombre_utilisateurs} utilisateur{e.nombre_utilisateurs > 1 ? "s" : ""} · {e.nombre_eleves} élève{e.nombre_eleves > 1 ? "s" : ""} · {e.niveau_abonnement}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={e.actif ? { backgroundColor: C.vertFond, color: C.vert } : { backgroundColor: C.rougeFond, color: C.rouge }}>
                    {e.actif ? "Actif" : "Désactivé"}
                  </span>
                  <button onClick={() => basculerActif(e)} className="eduai-focus flex items-center gap-1 text-xs font-medium" style={{ color: C.encreDoux }}>
                    <Power size={12} /> {e.actif ? "Désactiver" : "Réactiver"}
                  </button>
                </div>
              </div>
            ))}
            {etablissements.length === 0 && <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucun établissement pour l'instant.</p>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Documents (programmes officiels)                           */
/* ------------------------------------------------------------------ */

function BadgeStatutDocument({ statut }) {
  const map = {
    en_traitement: { label: "Indexation en cours...", bg: C.bleuFond, fg: C.encre },
    indexe: { label: "Indexé", bg: C.vertFond, fg: C.vert },
    erreur: { label: "Erreur d'indexation", bg: C.rougeFond, fg: C.rouge },
  };
  const s = map[statut] || map.en_traitement;
  return <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ backgroundColor: s.bg, color: s.fg }}>{s.label}</span>;
}

const PAYS_DISPONIBLES = [
  "Cameroun", "Sénégal", "Côte d'Ivoire", "République démocratique du Congo", "Bénin", "Togo", "Gabon",
];

function FormulaireDepotProgramme({ token, onDepose }) {
  const [ouvert, setOuvert] = useState(false);
  const [titre, setTitre] = useState("");
  const [pays, setPays] = useState(PAYS_DISPONIBLES[0]);
  const [fichier, setFichier] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);

  async function soumettre(e) {
    e.preventDefault();
    if (!fichier) { setErreur("Choisissez un fichier PDF."); return; }
    setEnvoi(true); setErreur(null);
    try {
      const formData = new FormData();
      formData.append("fichier", fichier);
      await apiFetch("/plateforme/documents", { method: "POST", token, params: { titre, pays }, body: formData });
      setTitre(""); setFichier(null); setOuvert(false);
      onDepose();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  if (!ouvert) {
    return (
      <button onClick={() => setOuvert(true)} className="eduai-focus flex items-center gap-1.5 text-xs font-medium" style={{ color: C.accentFonce }}>
        <Plus size={13} /> Déposer un programme officiel
      </button>
    );
  }

  return (
    <form onSubmit={soumettre} className="rounded-lg p-4 border space-y-2.5" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
      <BandeauErreur message={erreur} />
      <input required value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Titre (ex : Programme Maths 6ème — MINESEC)"
        className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
      <select value={pays} onChange={(e) => setPays(e.target.value)} required
        className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
        {PAYS_DISPONIBLES.map((p) => <option key={p} value={p}>{p}</option>)}
      </select>
      <label className="eduai-focus flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium border cursor-pointer w-fit" style={{ borderColor: C.ligne, color: C.encre, backgroundColor: C.surface }}>
        <Upload size={12} />{fichier ? fichier.name : "Choisir un PDF"}
        <input type="file" accept="application/pdf" className="hidden" onChange={(e) => setFichier(e.target.files[0] || null)} />
      </label>
      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={envoi} className="eduai-focus rounded-lg px-3.5 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {envoi ? <Loader2 size={12} className="eduai-spin" /> : "Déposer"}
        </button>
        <button type="button" onClick={() => setOuvert(false)} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
      </div>
    </form>
  );
}

function EcranDocuments({ token }) {
  const [documents, setDocuments] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/plateforme/documents", { token }).then(setDocuments).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function supprimer(id) {
    try {
      await apiFetch(`/plateforme/documents/${id}`, { method: "DELETE", token });
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (e) { setErreur(e.message); }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Documents</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        Programmes officiels utilisés par l'IA pour ancrer ses générations, visibles par toute la plateforme.
        Seul l'Admin Plateforme peut en déposer — les établissements peuvent seulement consulter la liste.
      </p>

      <BandeauErreur message={erreur} />

      <div className="rounded-2xl p-6 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <h2 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Programmes officiels</h2>
        <FormulaireDepotProgramme token={token} onDepose={charger} />

        {chargement ? <Chargement /> : (
          <div className="space-y-2 mt-5">
            {documents.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-lg border px-3 py-2.5" style={{ borderColor: C.ligne }}>
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileText size={15} color={C.encreAttenue} className="flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: C.encre }}>{d.titre}</p>
                    <p className="text-xs" style={{ color: C.encreAttenue }}>
                      {d.pays ? `${d.pays} · ` : ""}{[d.niveau, d.matiere].filter(Boolean).join(" · ") || "Niveau/matière non précisés"}
                      {d.nombre_pages ? ` · ${d.nombre_pages} page${d.nombre_pages > 1 ? "s" : ""}` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <BadgeStatutDocument statut={d.statut} />
                  <button onClick={() => supprimer(d.id)} className="eduai-focus" aria-label="Supprimer" style={{ color: C.encreAttenue }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
            {documents.length === 0 && <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucun programme officiel déposé pour l'instant.</p>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Bibliothèque commune d'exercices                           */
/* ------------------------------------------------------------------ */

function badgeColorForDifficulte(d) {
  if (d === "facile") return { bg: C.vertFond, fg: C.vert };
  if (d === "moyen") return { bg: C.ambreFond, fg: C.ambre };
  return { bg: C.rougeFond, fg: C.rouge };
}

function EcranBibliotheque({ token }) {
  const [exercices, setExercices] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/plateforme/exercices", { token }).then(setExercices).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function retirer(id) {
    try {
      await apiFetch(`/plateforme/exercices/${id}`, { method: "DELETE", token });
      setExercices((prev) => prev.filter((e) => e.id !== id));
    } catch (e) { setErreur(e.message); }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-2" style={{ color: C.encre }}>Bibliothèque commune</h1>
      <p className="text-sm mb-8" style={{ color: C.encreDoux }}>
        Exercices partagés entre tous les établissements de la plateforme (banque commune, pas rattachée à une école en particulier).
      </p>

      <BandeauErreur message={erreur} />

      <div className="rounded-2xl p-6 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        {chargement ? <Chargement /> : (
          <div className="space-y-2">
            {exercices.map((e) => {
              const badge = badgeColorForDifficulte(e.difficulte);
              return (
                <div key={e.id} className="flex items-center justify-between rounded-lg border px-3 py-2.5" style={{ borderColor: C.ligne }}>
                  <div className="flex items-center gap-2.5 min-w-0">
                    <BookMarked size={15} color={C.encreAttenue} className="flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: C.encre }}>{e.theme}</p>
                      <p className="text-xs" style={{ color: C.encreAttenue }}>{e.matiere} · {e.niveau} · {e.statut}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ backgroundColor: badge.bg, color: badge.fg }}>{e.difficulte}</span>
                    <button onClick={() => retirer(e.id)} className="eduai-focus" aria-label="Retirer" style={{ color: C.encreAttenue }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
            {exercices.length === 0 && <p className="text-sm text-center py-6" style={{ color: C.encreAttenue }}>Aucun exercice dans la bibliothèque commune pour l'instant.</p>}
          </div>
        )}
      </div>
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
  const [vue, setVue] = useState("etablissements");

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      await apiFetch("/plateforme/etablissements", { token: access_token });
      setToken(access_token);
    } catch (e) {
      setErreurConnexion(e.status === 401 ? "Ce compte n'a pas accès à cet espace." : e.message);
    }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() { setToken(null); setVue("etablissements"); }

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      {!token ? (
        <EcranConnexion onConnexion={connecter} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} />
          {vue === "etablissements" && <EcranEtablissements token={token} />}
          {vue === "documents" && <EcranDocuments token={token} />}
          {vue === "bibliotheque" && <EcranBibliotheque token={token} />}
        </>
      )}
    </div>
  );
}
