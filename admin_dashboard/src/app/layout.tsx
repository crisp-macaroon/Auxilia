import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { AppShell } from "@/components/layout/AppShell";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-poppins",
});

export const metadata: Metadata = {
  title: "Auxilia Admin | AI-Powered Parametric Insurance",
  description: "Admin dashboard for managing parametric insurance policies, claims, and riders",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${poppins.variable} h-full antialiased`}>
      <body suppressHydrationWarning className="min-h-full bg-white font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
