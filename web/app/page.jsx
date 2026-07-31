import Link from "next/link";
import { GraduationCap, BookOpen, ClipboardCheck, BarChart3, Users, Building2, Globe } from "lucide-react";

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

const ESPACES = [
  { href: "/eleve", label: "Élève", desc: "Exercices, corrigés, résultats", icon: BookOpen },
  { href: "/enseignant", label: "Enseignant", desc: "Cours, classes, validation", icon: ClipboardCheck },
  { href: "/direction", label: "Direction", desc: "Tableau de bord, pilotage", icon: BarChart3 },
  { href: "/parent", label: "Parent", desc: "Suivi scolaire de l'enfant", icon: Users },
  { href: "/administration", label: "Administration", desc: "Comptes, bulletins, paiements", icon: Building2 },
  { href: "/plateforme", label: "Admin Plateforme", desc: "Établissements, documents partagés", icon: Globe },
];

export default function Accueil() {
  return (
    <div className="eduai-root min-h-screen flex items-center justify-center px-6 py-16" style={{ backgroundColor: C.fond }}>
      <style>{STYLES}</style>
      <div className="w-full max-w-3xl">
        <div className="flex items-center justify-center gap-2 mb-3">
          <GraduationCap size={28} color={C.encre} strokeWidth={1.75} />
          <span className="eduai-display text-3xl" style={{ color: C.encre }}>
            ÉduAI <span style={{ color: C.accent }}>Afrique</span>
          </span>
        </div>
        <p className="text-center text-sm mb-12" style={{ color: C.encreDoux }}>
          Choisissez votre espace pour vous connecter.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {ESPACES.map((e) => (
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
  );
}
