"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GraduationCap, Lock, Mail, LogOut, Bell, Loader2, AlertTriangle,
  Users, Plus, UserX, ScrollText, Send, Wallet, Check, Copy,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Configuration API                                                  */
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
/*  Styles + palette                                                    */
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
          <h1 className="eduai-display text-xl mb-1" style={{ color: C.encre }}>Espace Administration</h1>
          <p className="text-sm mb-7" style={{ color: C.encreDoux }}>Connecte-toi pour gérer l'établissement.</p>
          <BandeauErreur message={erreurConnexion} />
          <form onSubmit={(e) => { e.preventDefault(); onConnexion(email, motDePasse); }} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium mb-1.5 flex items-center gap-1.5" style={{ color: C.encreDoux }}><Mail size={13} /> Adresse email</span>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="secretariat@ecole.cm"
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
    { id: "utilisateurs", label: "Utilisateurs" },
    { id: "bulletins", label: "Bulletins" },
    { id: "notifications", label: "Notifications" },
    { id: "paiements", label: "Paiements" },
  ];
  return (
    <div className="sticky top-0 z-10 px-4 sm:px-8 py-3.5 flex items-center justify-between border-b flex-wrap gap-y-2"
      style={{ backgroundColor: "rgba(250,248,243,0.92)", backdropFilter: "blur(6px)", borderColor: C.ligne }}>
      <button onClick={() => setVue("utilisateurs")} className="eduai-focus flex items-center gap-2">
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
/*  Écran : Utilisateurs                                                */
/* ------------------------------------------------------------------ */

function EcranUtilisateurs({ token, classes, matieres }) {
  const [utilisateurs, setUtilisateurs] = useState([]);
  const [filtreRole, setFiltreRole] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [modalCreation, setModalCreation] = useState(null); // 'eleve' | 'enseignant' | null

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/administration/utilisateurs", { token, params: { role: filtreRole } })
      .then(setUtilisateurs).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token, filtreRole]);

  useEffect(() => { charger(); }, [charger]);

  async function desactiver(id) {
    try {
      await apiFetch(`/administration/utilisateurs/${id}/desactiver`, { method: "PATCH", token });
      charger();
    } catch (e) { setErreur(e.message); }
  }

  const roles = [
    { id: null, label: "Tous" }, { id: "eleve", label: "Élèves" }, { id: "enseignant", label: "Enseignants" },
    { id: "direction", label: "Direction" }, { id: "administratif", label: "Administratif" }, { id: "parent", label: "Parents" },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="eduai-display text-3xl" style={{ color: C.encre }}>Utilisateurs</h1>
        <div className="flex gap-2">
          <button onClick={() => setModalCreation("eleve")} className="eduai-focus flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>
            <Plus size={13} /> Élève
          </button>
          <button onClick={() => setModalCreation("enseignant")} className="eduai-focus flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold border" style={{ borderColor: C.ligne, color: C.encre }}>
            <Plus size={13} /> Enseignant
          </button>
          <button onClick={() => setModalCreation("parent")} className="eduai-focus flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold border" style={{ borderColor: C.ligne, color: C.encre }}>
            <Plus size={13} /> Parent
          </button>
        </div>
      </div>

      <BandeauErreur message={erreur} />

      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {roles.map((r) => (
          <button key={r.id || "tous"} onClick={() => setFiltreRole(r.id)}
            className="eduai-focus whitespace-nowrap px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors border"
            style={{ backgroundColor: filtreRole === r.id ? C.encre : C.surface, color: filtreRole === r.id ? C.surface : C.encreDoux, borderColor: filtreRole === r.id ? C.encre : C.ligne }}>
            {r.label}
          </button>
        ))}
      </div>

      {chargement ? <Chargement /> : (
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
          {utilisateurs.map((u, i) => (
            <div key={u.id} className="px-5 py-3.5 flex items-center justify-between" style={{ borderTop: i > 0 ? `1px solid ${C.ligne}` : "none", opacity: u.actif ? 1 : 0.5 }}>
              <div>
                <p className="text-sm font-medium" style={{ color: C.encre }}>{u.nom} {u.prenom}</p>
                <p className="text-xs mt-0.5" style={{ color: C.encreDoux }}>{u.email || "—"} · {u.role}{u.classe ? ` · ${u.classe}` : ""}</p>
              </div>
              {u.actif ? (
                <button onClick={() => desactiver(u.id)} className="eduai-focus flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full" style={{ backgroundColor: C.rougeFond, color: C.rouge }}>
                  <UserX size={11} /> Désactiver
                </button>
              ) : (
                <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.fond, color: C.encreAttenue }}>Désactivé</span>
              )}
            </div>
          ))}
          {utilisateurs.length === 0 && <p className="text-sm px-5 py-6" style={{ color: C.encreDoux }}>Aucun utilisateur trouvé.</p>}
        </div>
      )}

      {modalCreation === "eleve" && <ModalCreationEleve token={token} classes={classes} onFerme={() => setModalCreation(null)} onCree={charger} />}
      {modalCreation === "enseignant" && <ModalCreationEnseignant token={token} classes={classes} matieres={matieres} onFerme={() => setModalCreation(null)} onCree={charger} />}
      {modalCreation === "parent" && <ModalCreationParent token={token} onFerme={() => setModalCreation(null)} onCree={charger} />}
    </div>
  );
}

function ModalCreationEleve({ token, classes, onFerme, onCree }) {
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [classeId, setClasseId] = useState(classes[0]?.id || "");
  const [matricule, setMatricule] = useState("");
  const [ajouterParent, setAjouterParent] = useState(false);
  const [parentEmail, setParentEmail] = useState("");
  const [parentNom, setParentNom] = useState("");
  const [parentPrenom, setParentPrenom] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);
  const [resultatEleve, setResultatEleve] = useState(null);
  const [resultatParent, setResultatParent] = useState(null);
  const [erreurParent, setErreurParent] = useState(null);

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null);
    try {
      const nouvelEleve = await apiFetch("/administration/eleves", {
        method: "POST", token,
        body: { email, nom, prenom, classe_id: classeId, matricule: matricule || null },
      });
      setResultatEleve(nouvelEleve);
      onCree();

      // Le compte élève est créé, quoi qu'il arrive ensuite avec le parent —
      // on ne fait donc jamais dépendre son succès de la création du parent.
      if (ajouterParent && parentEmail) {
        try {
          const nouveauParent = await apiFetch("/administration/parents", {
            method: "POST", token,
            body: { email: parentEmail, nom: parentNom, prenom: parentPrenom, eleve_ids: [nouvelEleve.id] },
          });
          setResultatParent(nouveauParent);
        } catch (eParent) {
          setErreurParent(`Élève créé, mais le compte parent a échoué : ${eParent.message} `
            + `(vous pourrez réessayer depuis "+ Parent" une fois cette fenêtre fermée).`);
        }
      }
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center px-6" style={{ backgroundColor: "rgba(34,48,74,0.45)" }}>
      <div className="w-full max-w-sm rounded-2xl p-6 eduai-fade-in max-h-[90vh] overflow-y-auto" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
        <h3 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Nouvel élève</h3>
        {resultatEleve ? (
          <div>
            <BandeauSucces message="Élève créé." />
            <p className="text-xs mb-1" style={{ color: C.encreDoux }}>Mot de passe provisoire de l'élève :</p>
            <div className="eduai-mono text-sm rounded-lg px-3 py-2 mb-4 flex items-center justify-between" style={{ backgroundColor: C.fond, color: C.encre }}>
              {resultatEleve.mot_de_passe_provisoire}
              <Copy size={13} color={C.encreAttenue} className="cursor-pointer" onClick={() => navigator.clipboard?.writeText(resultatEleve.mot_de_passe_provisoire)} />
            </div>

            {resultatParent && (
              <>
                <BandeauSucces message="Parent créé et lié à l'élève." />
                <p className="text-xs mb-1" style={{ color: C.encreDoux }}>Mot de passe provisoire du parent ({resultatParent.email}) :</p>
                <div className="eduai-mono text-sm rounded-lg px-3 py-2 mb-4 flex items-center justify-between" style={{ backgroundColor: C.fond, color: C.encre }}>
                  {resultatParent.mot_de_passe_provisoire}
                  <Copy size={13} color={C.encreAttenue} className="cursor-pointer" onClick={() => navigator.clipboard?.writeText(resultatParent.mot_de_passe_provisoire)} />
                </div>
              </>
            )}
            {erreurParent && <BandeauErreur message={erreurParent} />}

            <button onClick={onFerme} className="eduai-focus w-full rounded-lg py-2.5 text-sm font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>Fermer</button>
          </div>
        ) : (
          <form onSubmit={soumettre} className="space-y-3">
            <BandeauErreur message={erreur} />
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email de l'élève"
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            <div className="grid grid-cols-2 gap-2">
              <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
              <input required value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            </div>
            <select value={classeId} onChange={(e) => setClasseId(e.target.value)}
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
            <input value={matricule} onChange={(e) => setMatricule(e.target.value)} placeholder="Matricule (optionnel)"
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />

            <label className="flex items-center gap-2 text-xs pt-1" style={{ color: C.encreDoux }}>
              <input type="checkbox" checked={ajouterParent} onChange={(e) => setAjouterParent(e.target.checked)} />
              Inviter aussi un parent, lié à cet élève
            </label>

            {ajouterParent && (
              <div className="rounded-lg p-3 border space-y-2" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
                <input required={ajouterParent} type="email" value={parentEmail} onChange={(e) => setParentEmail(e.target.value)} placeholder="Email du parent"
                  className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
                <div className="grid grid-cols-2 gap-2">
                  <input required={ajouterParent} value={parentNom} onChange={(e) => setParentNom(e.target.value)} placeholder="Nom du parent"
                    className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
                  <input required={ajouterParent} value={parentPrenom} onChange={(e) => setParentPrenom(e.target.value)} placeholder="Prénom du parent"
                    className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }} />
                </div>
                <p className="text-[11px]" style={{ color: C.encreAttenue }}>
                  Un second parent (ou un parent pour un élève existant) peut être ajouté séparément via "+ Parent".
                </p>
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={envoi} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                {envoi && <Loader2 size={12} className="eduai-spin" />} Créer
              </button>
              <button type="button" onClick={onFerme} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function ModalCreationEnseignant({ token, classes, matieres, onFerme, onCree }) {
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [specialite, setSpecialite] = useState("");
  const [affectations, setAffectations] = useState([]);
  const [classeChoisie, setClasseChoisie] = useState(classes[0]?.id || "");
  const [matiereChoisie, setMatiereChoisie] = useState(matieres[0]?.id || "");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);
  const [resultat, setResultat] = useState(null);

  function ajouterAffectation() {
    const existe = affectations.some((a) => a.classe_id === classeChoisie && a.matiere_id === matiereChoisie);
    if (!existe) setAffectations((prev) => [...prev, { classe_id: classeChoisie, matiere_id: matiereChoisie }]);
  }

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null);
    try {
      const r = await apiFetch("/administration/enseignants", { method: "POST", token, body: { email, nom, prenom, specialite: specialite || null, affectations } });
      setResultat(r); onCree();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  const nomClasse = (id) => classes.find((c) => c.id === id)?.nom || id;
  const nomMatiere = (id) => matieres.find((m) => m.id === id)?.nom || id;

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center px-6" style={{ backgroundColor: "rgba(34,48,74,0.45)" }}>
      <div className="w-full max-w-sm rounded-2xl p-6 eduai-fade-in max-h-[90vh] overflow-y-auto" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
        <h3 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Nouvel enseignant</h3>
        {resultat ? (
          <div>
            <BandeauSucces message="Compte créé." />
            <p className="text-xs mb-1" style={{ color: C.encreDoux }}>Mot de passe provisoire :</p>
            <div className="eduai-mono text-sm rounded-lg px-3 py-2 mb-4" style={{ backgroundColor: C.fond, color: C.encre }}>{resultat.mot_de_passe_provisoire}</div>
            <button onClick={onFerme} className="eduai-focus w-full rounded-lg py-2.5 text-sm font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>Fermer</button>
          </div>
        ) : (
          <form onSubmit={soumettre} className="space-y-3">
            <BandeauErreur message={erreur} />
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            <div className="grid grid-cols-2 gap-2">
              <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
              <input required value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            </div>
            <input value={specialite} onChange={(e) => setSpecialite(e.target.value)} placeholder="Spécialité (optionnel)"
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />

            <div className="rounded-lg p-3 border" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
              <p className="text-xs font-medium mb-2" style={{ color: C.encreDoux }}>Affectations (classe + matière)</p>
              <div className="flex gap-2 mb-2">
                <select value={classeChoisie} onChange={(e) => setClasseChoisie(e.target.value)} className="eduai-focus flex-1 rounded-lg px-2 py-1.5 text-xs outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
                  {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
                </select>
                <select value={matiereChoisie} onChange={(e) => setMatiereChoisie(e.target.value)} className="eduai-focus flex-1 rounded-lg px-2 py-1.5 text-xs outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.surface, color: C.encre }}>
                  {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom}</option>)}
                </select>
                <button type="button" onClick={ajouterAffectation} className="eduai-focus rounded-lg px-2.5 text-xs font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>+</button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {affectations.map((a, i) => (
                  <span key={i} className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                    {nomClasse(a.classe_id)} · {nomMatiere(a.matiere_id)}
                  </span>
                ))}
                {affectations.length === 0 && <span className="text-[11px]" style={{ color: C.encreAttenue }}>Aucune affectation ajoutée</span>}
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={envoi} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                {envoi && <Loader2 size={12} className="eduai-spin" />} Créer
              </button>
              <button type="button" onClick={onFerme} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function ModalCreationParent({ token, onFerme, onCree }) {
  const [eleves, setEleves] = useState([]);
  const [chargementEleves, setChargementEleves] = useState(true);
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [elevesChoisis, setElevesChoisis] = useState([]);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);
  const [resultat, setResultat] = useState(null);

  useEffect(() => {
    // Chargée indépendamment du filtre de l'écran principal — sinon, si
    // l'admin avait "Enseignants" sélectionné en arrivant ici, la liste
    // des élèves disponibles serait vide.
    apiFetch("/administration/utilisateurs", { token, params: { role: "eleve" } })
      .then(setEleves).catch(() => {}).finally(() => setChargementEleves(false));
  }, [token]);

  function basculerEleve(id) {
    setElevesChoisis((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null);
    try {
      const r = await apiFetch("/administration/parents", { method: "POST", token, body: { email, nom, prenom, eleve_ids: elevesChoisis } });
      setResultat(r); onCree();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center px-6" style={{ backgroundColor: "rgba(34,48,74,0.45)" }}>
      <div className="w-full max-w-sm rounded-2xl p-6 eduai-fade-in max-h-[90vh] overflow-y-auto" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre }}>
        <h3 className="eduai-display text-lg mb-4" style={{ color: C.encre }}>Nouveau parent</h3>
        {resultat ? (
          <div>
            <BandeauSucces message="Compte créé." />
            <p className="text-xs mb-1" style={{ color: C.encreDoux }}>Mot de passe provisoire :</p>
            <div className="eduai-mono text-sm rounded-lg px-3 py-2 mb-4" style={{ backgroundColor: C.fond, color: C.encre }}>{resultat.mot_de_passe_provisoire}</div>
            <button onClick={onFerme} className="eduai-focus w-full rounded-lg py-2.5 text-sm font-semibold" style={{ backgroundColor: C.encre, color: C.surface }}>Fermer</button>
          </div>
        ) : (
          <form onSubmit={soumettre} className="space-y-3">
            <BandeauErreur message={erreur} />
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
              className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            <div className="grid grid-cols-2 gap-2">
              <input required value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
              <input required value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom"
                className="eduai-focus rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
            </div>

            <div className="rounded-lg p-3 border" style={{ borderColor: C.ligne, backgroundColor: C.fond }}>
              <p className="text-xs font-medium mb-2" style={{ color: C.encreDoux }}>Enfant(s) à lier</p>
              {chargementEleves ? (
                <p className="text-xs" style={{ color: C.encreAttenue }}>Chargement...</p>
              ) : eleves.length === 0 ? (
                <p className="text-xs" style={{ color: C.encreAttenue }}>Aucun élève trouvé — créez d'abord un compte élève.</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {eleves.map((el) => (
                    <label key={el.id} className="flex items-center gap-2 text-xs" style={{ color: C.encre }}>
                      <input type="checkbox" checked={elevesChoisis.includes(el.id)} onChange={() => basculerEleve(el.id)} />
                      {el.nom} {el.prenom} {el.classe ? `— ${el.classe}` : ""}
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={envoi || elevesChoisis.length === 0} className="eduai-focus flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                {envoi && <Loader2 size={12} className="eduai-spin" />} Créer
              </button>
              <button type="button" onClick={onFerme} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Bulletins                                                   */
/* ------------------------------------------------------------------ */

function EcranBulletins({ token, classes }) {
  const [classeId, setClasseId] = useState(classes[0]?.id || "");
  const [trimestre, setTrimestre] = useState(1);
  const [resultats, setResultats] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);

  async function generer() {
    setEnvoi(true); setErreur(null); setResultats(null);
    try {
      const r = await apiFetch("/administration/bulletins/generer", { method: "POST", token, body: { classe_id: classeId, trimestre } });
      setResultats(r.sort((a, b) => (a.rang_classe || 999) - (b.rang_classe || 999)));
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Générer les bulletins</h1>

      <div className="rounded-2xl p-7 border mb-6" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <BandeauErreur message={erreur} />
        <div className="grid grid-cols-2 gap-3 mb-4">
          <label className="block">
            <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Classe</span>
            <select value={classeId} onChange={(e) => setClasseId(e.target.value)} className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
              {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Trimestre</span>
            <select value={trimestre} onChange={(e) => setTrimestre(parseInt(e.target.value))} className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
              {[1, 2, 3].map((t) => <option key={t} value={t}>Trimestre {t}</option>)}
            </select>
          </label>
        </div>
        <button onClick={generer} disabled={envoi} className="eduai-focus flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {envoi ? <Loader2 size={15} className="eduai-spin" /> : <ScrollText size={15} />} Générer
        </button>
      </div>

      {resultats && (
        <div className="space-y-2.5">
          {resultats.map((b) => (
            <div key={b.eleve_id} className="rounded-xl px-5 py-3.5 flex items-center justify-between border" style={{ backgroundColor: C.surface, borderColor: C.ligne }}>
              <span className="text-sm font-medium" style={{ color: C.encre }}>{b.eleve_nom}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs" style={{ color: C.encreDoux }}>{b.rang_classe ? `Rang ${b.rang_classe}` : "—"}</span>
                <span className="eduai-mono text-sm font-bold" style={{ color: C.accentFonce }}>{b.moyenne_generale === null ? "—" : `${b.moyenne_generale}/20`}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Notifications (diffusion)                                   */
/* ------------------------------------------------------------------ */

function EcranNotificationsDiffusion({ token, classes }) {
  const [classeId, setClasseId] = useState(classes[0]?.id || "");
  const [titre, setTitre] = useState("");
  const [message, setMessage] = useState("");
  const [inclureParents, setInclureParents] = useState(true);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(null);
  const [succes, setSucces] = useState(null);

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true); setErreur(null); setSucces(null);
    try {
      const r = await apiFetch("/administration/notifications/diffuser", { method: "POST", token, body: { titre, message, classe_id: classeId, inclure_parents: inclureParents } });
      setSucces(`${r.nombre_notifications_envoyees} notification(s) envoyée(s).`);
      setTitre(""); setMessage("");
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Diffuser une notification</h1>
      <form onSubmit={soumettre} className="rounded-2xl p-7 border space-y-4" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
        <BandeauErreur message={erreur} />
        <BandeauSucces message={succes} />
        <label className="block">
          <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Classe destinataire</span>
          <select value={classeId} onChange={(e) => setClasseId(e.target.value)} className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }}>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Titre</span>
          <input required value={titre} onChange={(e) => setTitre(e.target.value)} className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
        </label>
        <label className="block">
          <span className="text-xs font-medium mb-1 block" style={{ color: C.encreDoux }}>Message</span>
          <textarea required value={message} onChange={(e) => setMessage(e.target.value)} rows={4} className="eduai-focus w-full rounded-lg px-3 py-2 text-sm outline-none border" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre, resize: "vertical" }} />
        </label>
        <label className="flex items-center gap-2 text-xs" style={{ color: C.encreDoux }}>
          <input type="checkbox" checked={inclureParents} onChange={(e) => setInclureParents(e.target.checked)} /> Inclure les parents
        </label>
        <button type="submit" disabled={envoi} className="eduai-focus flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
          {envoi ? <Loader2 size={15} className="eduai-spin" /> : <Send size={15} />} Diffuser
        </button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Écran : Paiements                                                   */
/* ------------------------------------------------------------------ */

function EcranPaiements({ token }) {
  const [paiements, setPaiements] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);
  const [encaissementId, setEncaissementId] = useState(null);
  const [montant, setMontant] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const charger = useCallback(() => {
    setChargement(true); setErreur(null);
    apiFetch("/administration/paiements", { token }).then(setPaiements).catch((e) => setErreur(e.message)).finally(() => setChargement(false));
  }, [token]);

  useEffect(() => { charger(); }, [charger]);

  async function encaisser(id) {
    setEnvoi(true); setErreur(null);
    try {
      await apiFetch(`/administration/paiements/${id}/encaisser`, { method: "POST", token, body: { montant: parseFloat(montant) } });
      setEncaissementId(null); setMontant(""); charger();
    } catch (e) { setErreur(e.message); }
    finally { setEnvoi(false); }
  }

  const statutLabel = { en_attente: "En attente", partiel: "Partiel", complet: "Complet" };
  const statutCouleur = { en_attente: { bg: C.rougeFond, fg: C.rouge }, partiel: { bg: C.ambreFond, fg: C.ambre }, complet: { bg: C.vertFond, fg: C.vert } };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-10 eduai-fade-in">
      <h1 className="eduai-display text-3xl mb-8" style={{ color: C.encre }}>Paiements</h1>
      <BandeauErreur message={erreur} />
      {chargement ? <Chargement /> : (
        <div className="space-y-3">
          {paiements.map((p) => {
            const s = statutCouleur[p.statut] || statutCouleur.en_attente;
            return (
              <div key={p.id} className="rounded-xl p-5 border" style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold flex items-center gap-1.5" style={{ color: C.encre }}>
                    <Wallet size={14} color={C.accentFonce} /> {p.eleve_nom} {p.eleve_prenom}
                  </span>
                  <span className="eduai-mono text-[10px] px-2 py-0.5 rounded-full" style={{ backgroundColor: s.bg, color: s.fg }}>{statutLabel[p.statut]}</span>
                </div>
                <p className="eduai-mono text-xs mb-3" style={{ color: C.encreDoux }}>
                  {p.classe} · {p.montant_paye.toLocaleString("fr-FR")} / {p.montant_du.toLocaleString("fr-FR")} FCFA
                  {p.date_echeance && ` · échéance ${new Date(p.date_echeance).toLocaleDateString("fr-FR")}`}
                </p>
                {encaissementId === p.id ? (
                  <div className="flex gap-2 items-center">
                    <input autoFocus type="number" value={montant} onChange={(e) => setMontant(e.target.value)} placeholder="Montant reçu"
                      className="eduai-focus rounded-lg px-3 py-1.5 text-xs outline-none border flex-1" style={{ borderColor: C.ligne, backgroundColor: C.fond, color: C.encre }} />
                    <button onClick={() => encaisser(p.id)} disabled={envoi || !montant} className="eduai-focus rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-60" style={{ backgroundColor: C.encre, color: C.surface }}>
                      {envoi ? <Loader2 size={12} className="eduai-spin" /> : "Valider"}
                    </button>
                    <button onClick={() => { setEncaissementId(null); setMontant(""); }} className="eduai-focus text-xs font-medium" style={{ color: C.encreDoux }}>Annuler</button>
                  </div>
                ) : p.statut !== "complet" ? (
                  <button onClick={() => setEncaissementId(p.id)} className="eduai-focus text-xs font-medium px-3 py-1.5 rounded-full" style={{ backgroundColor: C.bleuFond, color: C.encre }}>
                    Encaisser un paiement
                  </button>
                ) : null}
              </div>
            );
          })}
          {paiements.length === 0 && <p className="text-sm" style={{ color: C.encreDoux }}>Aucun paiement enregistré.</p>}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Application                                                        */
/* ------------------------------------------------------------------ */

export default function EspaceAdministration() {
  const [token, setToken] = useState(null);
  const [connexionEnCours, setConnexionEnCours] = useState(false);
  const [erreurConnexion, setErreurConnexion] = useState(null);
  const [vue, setVue] = useState("utilisateurs");
  const [classes, setClasses] = useState([]);
  const [matieres, setMatieres] = useState([]);

  async function connecter(email, motDePasse) {
    setConnexionEnCours(true); setErreurConnexion(null);
    try {
      const { access_token } = await apiFetch("/auth/login", { method: "POST", body: { email, mot_de_passe: motDePasse } });
      setToken(access_token);
    } catch (e) { setErreurConnexion(e.message); }
    finally { setConnexionEnCours(false); }
  }

  function deconnecter() { setToken(null); setVue("utilisateurs"); }

  useEffect(() => {
    if (!token) return;
    apiFetch("/administration/classes", { token }).then(setClasses).catch(() => {});
    apiFetch("/administration/matieres", { token }).then(setMatieres).catch(() => {});
  }, [token]);

  return (
    <div className="eduai-root min-h-screen" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      {!token ? (
        <EcranConnexion onConnexion={connecter} connexionEnCours={connexionEnCours} erreurConnexion={erreurConnexion} />
      ) : (
        <>
          <BarreNav vue={vue} setVue={setVue} onDeconnexion={deconnecter} />
          {vue === "utilisateurs" && <EcranUtilisateurs token={token} classes={classes} matieres={matieres} />}
          {vue === "bulletins" && <EcranBulletins token={token} classes={classes} />}
          {vue === "notifications" && <EcranNotificationsDiffusion token={token} classes={classes} />}
          {vue === "paiements" && <EcranPaiements token={token} />}
        </>
      )}
    </div>
  );
}
