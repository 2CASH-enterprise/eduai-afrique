import "./globals.css";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";
import ErrorBoundary from "@/components/ErrorBoundary";

export const metadata = {
  title: "OskarAI",
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
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
