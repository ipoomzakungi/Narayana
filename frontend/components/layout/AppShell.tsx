"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

const navItems = [
  { href: "/", label: "Cases", description: "operator dashboard" },
  { href: "/call-audit", label: "Call Audit", description: "session timeline" },
  { href: "/voice-debug", label: "Voice Debug", description: "manual test tools" }
];

function navClass(active: boolean) {
  return [
    "border px-3 py-2 text-sm font-semibold transition-colors",
    active
      ? "border-slate-950 bg-slate-950 text-white"
      : "border-command-line bg-white text-slate-800 hover:border-slate-950 hover:bg-slate-100"
  ].join(" ");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#eef1f5] text-slate-950">
      <header className="sticky top-0 z-20 border-b border-command-line bg-[#eef1f5]/95 px-4 py-3 backdrop-blur md:px-8">
        <div className="mx-auto flex w-full max-w-[calc(100vw-2rem)] flex-col gap-3 lg:max-w-7xl lg:flex-row lg:items-center lg:justify-between">
          <Link className="block" href="/" aria-label="Open Narayana cases dashboard">
            <div className="text-lg font-semibold tracking-normal text-slate-950">Narayana</div>
            <div className="text-xs font-medium text-slate-600">Realtime crisis intake dashboard</div>
          </Link>

          <nav className="flex flex-wrap items-center gap-2" aria-label="Primary navigation">
            {navItems.map((item) => {
              const active = item.href === "/" ? pathname === "/" || pathname === "/cases" : pathname.startsWith(item.href);
              return (
                <Link key={item.href} className={navClass(active)} href={item.href} title={item.description}>
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="mx-auto mt-3 flex w-full max-w-[calc(100vw-2rem)] flex-wrap gap-2 text-xs text-slate-700 lg:max-w-7xl">
          <span className="border border-command-line bg-white px-2 py-1">Backend: Azure Container Apps</span>
          <span className="border border-command-line bg-white px-2 py-1">Realtime: gpt-realtime-1.5</span>
          <span className="border border-command-line bg-white px-2 py-1">Storage: Cosmos DB</span>
        </div>
      </header>

      <main className="px-4 py-5 md:px-8">{children}</main>
    </div>
  );
}
