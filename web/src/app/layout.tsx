import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Masar | مسار — Smart Banking",
  description: "Egyptian digital banking, live markets, AI recommendations and a Llama assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
