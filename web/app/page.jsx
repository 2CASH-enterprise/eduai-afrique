import Link from "next/link";
import { GraduationCap, BookOpen, ClipboardCheck, BarChart3, Users, Building2 } from "lucide-react";

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
  .eduai-root { font-family: 'IBM Plex Sans', sans-serif; }
  .eduai-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; }
`;

const C = {
  fond: "#FAF8F3",
  surface: "#FFFFFF",
  surfaceOmbre: "0 12px 32px -16px rgba(34,48,74,0.16), 0 2px 8px -4px rgba(34,48,74,0.08)",
  ligne: "#E7E2D6",
  encre: "#22304A",
  encreDoux: "#5B6472",
  accent: "#B08D57",
  accentFonce: "#8F7140",
};

// Admin Plateforme n'apparaît volontairement jamais ici — outil interne
// pour l'équipe, retiré définitivement du portail public (accessible par
// URL directe uniquement), pas "en attente d'activation" comme les autres
// (voir TODO.md, discuté le 05/08).
const ESPACES = [
  { module: "eleve", href: "/eleve", label: "Élève", desc: "Exercices, corrigés, résultats", icon: BookOpen },
  { module: "enseignant", href: "/enseignant", label: "Enseignant", desc: "Cours, classes, validation", icon: ClipboardCheck },
  { module: "direction", href: "/direction", label: "Direction", desc: "Tableau de bord, pilotage", icon: BarChart3 },
  { module: "parent", href: "/parent", label: "Parent", desc: "Suivi scolaire de l'enfant", icon: Users },
  { module: "administration", href: "/administration", label: "Administration", desc: "Comptes, bulletins, paiements", icon: Building2 },
];

const API_BASE_URL = "http://178.104.56.200:8000";

async function chargerModulesActifs() {
  try {
    const reponse = await fetch(`${API_BASE_URL}/modules-actifs`, { next: { revalidate: 60 } });
    if (!reponse.ok) return new Set(["enseignant"]); // repli sûr si l'API est indisponible
    const donnees = await reponse.json();
    return new Set(donnees.filter((m) => m.actif).map((m) => m.module));
  } catch {
    return new Set(["enseignant"]); // repli sûr — jamais une page blanche si l'API est injoignable
  }
}

export default async function Accueil() {
  const modulesActifs = await chargerModulesActifs();
  const espacesVisibles = ESPACES.filter((e) => modulesActifs.has(e.module));

  return (
    <div className="eduai-root min-h-screen flex flex-col" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-3xl">
          <div className="flex items-center justify-center gap-2 mb-3">
            <GraduationCap size={28} color={C.encre} strokeWidth={1.75} />
            <span className="eduai-display text-3xl" style={{ color: C.encre }}>
              Oskar<span style={{ color: C.accent }}>AI</span>
            </span>
          </div>
          <p className="text-center text-sm mb-1" style={{ color: C.encreDoux }}>
            Plateforme pédagogique intelligente, enrichie par les programmes officiels d'Afrique francophone.
          </p>
          <p className="text-center text-sm mb-12" style={{ color: C.encreDoux }}>
            Choisissez votre espace pour vous connecter.
          </p>

          <div className={`grid grid-cols-1 ${espacesVisibles.length > 1 ? "sm:grid-cols-2" : ""} gap-4`}>
            {espacesVisibles.map((e) => (
              <Link
                key={e.href}
                href={e.href}
                className="rounded-xl p-6 border transition-transform hover:-translate-y-0.5 flex items-start gap-4"
                style={{ backgroundColor: C.surface, boxShadow: C.surfaceOmbre, borderColor: C.ligne }}
              >
                <e.icon size={22} color={C.accentFonce} className="mt-0.5 flex-shrink-0" />
                <div>
                  <p className="eduai-display text-lg" style={{ color: C.encre }}>{e.label}</p>
                  <p className="text-xs mt-1" style={{ color: C.encreDoux }}>{e.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <footer className="px-6 py-6 text-center border-t" style={{ borderColor: C.ligne }}>
        <p className="text-xs" style={{ color: C.encreDoux }}>
          © {new Date().getFullYear()} OskarAI
          <span className="mx-2">·</span>
          <Link href="/cgu" className="hover:underline" style={{ color: C.encreDoux }}>Conditions d'utilisation</Link>
          <span className="mx-2">·</span>
          <Link href="/confidentialite" className="hover:underline" style={{ color: C.encreDoux }}>Confidentialité</Link>
        </p>
      </footer>
    </div>
  );
}
