import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Narayana AI Voice Gateway",
  description: "Local-first Azure voice intake and triage debug console"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
