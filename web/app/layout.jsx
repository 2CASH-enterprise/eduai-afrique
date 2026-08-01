import "./globals.css";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";

export const metadata = {
  title: "ÉduAI Afrique",
  description: "Plateforme pédagogique intelligente pour l'Afrique francophone",
  manifest: "/manifest.json",
};

export const viewport = {
  themeColor: "#22304A",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
