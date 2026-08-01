"use client";

import { useEffect, useState } from "react";

export default function ServiceWorkerRegistration() {
  const [horsLigne, setHorsLigne] = useState(false);

  useEffect(() => {
    // Reflète l'état réel du navigateur, pas une estimation — se met à jour
    // automatiquement à la perte/reprise de connexion.
    setHorsLigne(!navigator.onLine);
    const surHorsLigne = () => setHorsLigne(true);
    const surEnLigne = () => setHorsLigne(false);
    window.addEventListener("offline", surHorsLigne);
    window.addEventListener("online", surEnLigne);

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Échoue silencieusement si le navigateur refuse (HTTP non
        // sécurisé, par exemple — voir TODO.md point 4) : l'app continue
        // de fonctionner normalement, juste sans le bénéfice hors-ligne.
      });
    }

    return () => {
      window.removeEventListener("offline", surHorsLigne);
      window.removeEventListener("online", surEnLigne);
    };
  }, []);

  if (!horsLigne) return null;

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        backgroundColor: "#F5EBD8",
        color: "#63380B",
        fontSize: "13px",
        fontFamily: "'IBM Plex Sans', sans-serif",
        textAlign: "center",
        padding: "6px 12px",
      }}
    >
      Hors-ligne — vous consultez une copie déjà chargée. Certaines actions (génération, validation, connexion) ne fonctionneront pas tant que le réseau n'est pas revenu.
    </div>
  );
}
