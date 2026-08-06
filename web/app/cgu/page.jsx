import Link from "next/link";

const C = {
  fond: "#FAF8F3", surface: "#FFFFFF", ligne: "#E7E2D6",
  encre: "#22304A", encreDoux: "#5B6472", accent: "#B08D57",
};

export const metadata = { title: "Conditions Générales d'Utilisation — OskarAI" };

export default function CGU() {
  return (
    <div className="eduai-root min-h-screen px-6 py-16" style={{ backgroundColor: C.fond, fontFamily: "'IBM Plex Sans', sans-serif" }}>
      <div className="max-w-2xl mx-auto">
        <Link href="/" className="text-sm mb-8 inline-block" style={{ color: C.encreDoux }}>← Retour à l'accueil</Link>
        <h1 className="text-2xl font-semibold mb-4" style={{ color: C.encre }}>Conditions Générales d'Utilisation</h1>
        <div className="rounded-xl p-6 border text-sm leading-relaxed" style={{ backgroundColor: C.surface, borderColor: C.ligne, color: C.encreDoux }}>
          <p className="mb-3">
            Cette page est un espace réservé — le texte définitif des Conditions Générales d'Utilisation
            d'OskarAI n'a pas encore été rédigé.
          </p>
          <p>
            Pour toute question sur les conditions d'utilisation de la plateforme en attendant sa publication,
            contactez l'équipe OskarAI directement.
          </p>
        </div>
      </div>
    </div>
  );
}
