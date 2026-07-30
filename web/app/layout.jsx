import "./globals.css";

export const metadata = {
  title: "ÉduAI Afrique",
  description: "Plateforme pédagogique intelligente pour l'Afrique francophone",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
