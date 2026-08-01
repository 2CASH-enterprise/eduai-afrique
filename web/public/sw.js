// Service worker — périmètre V1 volontairement limité à la CONSULTATION
// hors-ligne (voir TODO.md point 4) : ce qui a déjà été chargé pendant
// qu'il y avait du réseau reste consultable sans réseau. Rien n'est
// synchronisé au retour de la connexion — les actions (répondre à un
// exercice, valider, etc.) exigent toujours une connexion active.
//
// Note : les service workers exigent HTTPS (sauf en localhost) — ce
// fichier reste inactif tant que l'application n'est pas servie derrière
// un certificat HTTPS (voir TODO.md point 4).

const CACHE_NOM = "eduai-afrique-v1";

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((noms) =>
      Promise.all(noms.filter((n) => n !== CACHE_NOM).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Jamais de cache pour ce qui modifie des données — seule la lecture
  // fonctionne hors-ligne dans cette V1. Une requête d'écriture hors-ligne
  // échoue normalement, comme avant ce service worker.
  if (request.method !== "GET") return;

  event.respondWith(
    fetch(request)
      .then((reponse) => {
        // On ne met en cache que les réponses réellement exploitables —
        // jamais une erreur, jamais une réponse opaque non lisible.
        if (reponse && reponse.status === 200 && reponse.type !== "opaque") {
          const copie = reponse.clone();
          caches.open(CACHE_NOM).then((cache) => cache.put(request, copie));
        }
        return reponse;
      })
      .catch(() =>
        caches.match(request).then((depuisLeCache) => {
          if (depuisLeCache) return depuisLeCache;
          // Rien en cache pour cette requête précise — on laisse l'erreur
          // réseau remonter normalement, l'app affichera son message
          // habituel ("Impossible de joindre l'API").
          throw new Error("Hors-ligne, et rien en cache pour cette requête");
        })
      )
  );
});
