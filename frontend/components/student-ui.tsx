import Link from "next/link";
import type { ReactNode } from "react";

export function Icon({ children, className = "" }: { children: string; className?: string }) {
  const icons: Record<string, ReactNode> = {
    search: <><circle cx="10.8" cy="10.8" r="6.3"/><path d="m15.5 15.5 4.2 4.2"/></>,
    add: <path d="M12 5v14M5 12h14"/>,
    arrow_forward: <><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></>,
    arrow_back: <><path d="M19 12H5"/><path d="m10 7-5 5 5 5"/></>,
    route: <><circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h5a3 3 0 0 1 0 6h-2a3 3 0 0 0 0 6h5"/></>,
    hub: <><circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="m10.2 10.2-3.7-3M13.8 10.2l3.7-3M10.2 13.8l-3.7 3M13.8 13.8l3.7 3"/></>,
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    grid_view: <><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></>,
    menu_book: <><path d="M3 5.5c3.5-1 6-.3 9 1.7v12c-3-2-5.5-2.7-9-1.7z"/><path d="M21 5.5c-3.5-1-6-.3-9 1.7v12c3-2 5.5-2.7 9-1.7z"/></>,
    description: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 12h6M9 16h6"/></>,
    upload_file: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M12 17V10m-3 3 3-3 3 3"/></>,
    code: <path d="m8 8-4 4 4 4m8-8 4 4-4 4m-2-11-4 14"/>,
    code_blocks: <><path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16"/></>,
    data_object: <path d="M8 3C5 3 4 5 4 8v1c0 2-1 3-2 3 1 0 2 1 2 3v1c0 3 1 5 4 5m8-18c3 0 4 2 4 5v1c0 2 1 3 2 3-1 0-2 1-2 3v1c0 3-1 5-4 5"/>,
    analytics: <><path d="M4 20V10m6 10V4m6 16v-7m5 7H2"/></>,
    psychology: <><path d="M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-1 5 3.5 3.5 0 0 0 4 5.5V4Zm6 0a3 3 0 0 1 3 3v1a3 3 0 0 1 1 5 3.5 3.5 0 0 1-4 5.5V4Z"/><path d="M9 9H7m8 4h2M9 15H7m8-6h2"/></>,
    psychology_alt: <><path d="M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-1 5 3.5 3.5 0 0 0 4 5.5V4Zm6 0a3 3 0 0 1 3 3v1a3 3 0 0 1 1 5 3.5 3.5 0 0 1-4 5.5V4Z"/><path d="M12 8v7m-2-4h4"/></>,
    quiz: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 8a3 3 0 1 1 3 3v2m0 3h.01"/></>,
    work: <><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18"/></>,
    school: <><path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11v5c3 3 9 3 12 0v-5m4-2v6"/></>,
    engineering: <><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2"/></>,
    precision_manufacturing: <><circle cx="7" cy="8" r="3"/><path d="M10 8h4l2 3h4v8h-9v-6H7v6H3v-8h4"/></>,
    architecture: <><path d="m4 20 6-16 3 1-6 15zM14 4l6 16m-8-7h7"/></>,
    construction: <><path d="m5 20 6-6m3-3 5-5"/><path d="M14 3a5 5 0 0 0 7 7l-4-1-2-2zM3 14l7 7"/></>,
    factory: <><path d="M3 21V9l6 3V9l6 3V4h6v17z"/><path d="M7 16h2m4 0h2m4 0h2"/></>,
    bolt: <path d="m13 2-8 12h7l-1 8 8-12h-7z"/>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6l-.3-2.6h-4L10.4 6A8 8 0 0 0 8 7.1l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1A8 8 0 0 0 10.4 18l.3 2.6h4L15 18a8 8 0 0 0 1.6-1.1l2.4 1 2-3.4-2-1.5a7 7 0 0 0 0-1Z"/></>,
    settings_suggest: <><circle cx="9" cy="12" r="3"/><path d="M9 3v3m0 12v3M3 12h3m6 0h3m4-7v6m-3-3h6"/></>,
    tune: <><path d="M4 6h6m4 0h6M4 12h10m4 0h2M4 18h3m4 0h9"/><circle cx="12" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="9" cy="18" r="2"/></>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-1 .4-1 1.2-1 2.2m0 3h.01"/></>,
    help_outline: <><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-1 .4-1 1.2-1 2.2m0 3h.01"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/></>,
    error: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 4h.01"/></>,
    block: <><circle cx="12" cy="12" r="9"/><path d="m6 6 12 12"/></>,
    cancel: <><circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/></>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    check_circle: <><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></>,
    verified: <><path d="m12 2 3 2 3.5.5.5 3.5 2 3-2 3-.5 3.5-3.5.5-3 2-3-2-3.5-.5-.5-3.5-2-3 2-3 .5-3.5 3.5-.5z"/><path d="m8.5 12 2 2 5-5"/></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
    play_arrow: <path d="m8 5 11 7-11 7z"/>,
    print: <><path d="M7 8V3h10v5M7 17v4h10v-4"/><rect x="3" y="8" width="18" height="10" rx="2"/><path d="M17 12h.01"/></>,
    map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15m6-12v15"/></>,
    design_services: <><path d="m4 20 8-8m3-3 5-5M14 3a5 5 0 0 0 7 7l-4-1-2-2z"/><path d="m3 14 7 7"/></>,
    stars: <path d="m12 3 2.2 4.8L19 10l-4.8 2.2L12 17l-2.2-4.8L5 10l4.8-2.2zM19 17v4m-2-2h4"/>,
    explore: <><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/></>,
    face_3: <><circle cx="12" cy="12" r="9"/><path d="M8.5 10h.01m7 0h.01M8 15c2.5 2 5.5 2 8 0M6 6c3-3 9-3 12 0"/></>,
    emoji_objects: <><path d="M9 18h6m-5 3h4"/><path d="M8 14a6 6 0 1 1 8 0c-1 .8-1.5 1.7-1.5 3h-5c0-1.3-.5-2.2-1.5-3Z"/></>,
    sentiment_very_dissatisfied: <><circle cx="12" cy="12" r="9"/><path d="M8 9h.01M16 9h.01M8 17c2-3 6-3 8 0"/></>,
    sentiment_dissatisfied: <><circle cx="12" cy="12" r="9"/><path d="M8 9h.01M16 9h.01m-7 7c2-2 4-2 6 0"/></>,
    sentiment_neutral: <><circle cx="12" cy="12" r="9"/><path d="M8 9h.01M16 9h.01M9 16h6"/></>,
    sentiment_satisfied: <><circle cx="12" cy="12" r="9"/><path d="M8 9h.01M16 9h.01m-7 6c2 2 4 2 6 0"/></>,
    sentiment_very_satisfied: <><circle cx="12" cy="12" r="9"/><path d="M8 9h.01M16 9h.01m-8 5c3 4 7 4 10 0"/></>,
  };
  return <svg className={`inline-block shrink-0 ${className}`} width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[children] ?? <circle cx="12" cy="12" r="7"/>}</svg>;
}

export function TopNav({ active = "Explore", brand = "SIIT Roadmap" }: { active?: string; brand?: string }) {
  const links = [
    ["Explore", "/"],
    ["Roadmaps", "/roadmap"],
    ["Library", "/targets"],
    ["Profile", "/portfolio"],
  ];
  return (
    <header className="bg-surface-bg border-b border-border-low sticky top-0 z-50">
      <div className="flex justify-between items-center h-16 px-gutter max-w-container-max mx-auto">
        <div className="flex items-center gap-8 min-w-0">
          <Link className="font-headline-md text-xl sm:text-headline-md font-bold text-on-surface whitespace-nowrap" href="/">{brand}</Link>
          <nav className="hidden md:flex gap-6">
            {links.map(([label, href]) => (
              <Link key={label} href={href} className={`font-body-md text-body-md pb-1 transition-colors ${active === label ? "text-primary border-b-2 border-primary" : "text-secondary hover:text-primary"}`}>{label}</Link>
            ))}
          </nav>
        </div>
        <Link href="/discover" className="font-body-md text-sm sm:text-body-md bg-primary text-on-primary px-4 py-2 rounded-lg hover:bg-primary-container transition-colors">Get Started</Link>
      </div>
    </header>
  );
}

export function DiscoverNav({ active = "Pathfinding" }: { active?: string }) {
  return (
    <header className="bg-surface-bg w-full sticky top-0 border-b border-border-low z-50">
      <div className="flex justify-between items-center h-16 px-gutter max-w-container-max mx-auto">
        <div className="flex items-center gap-stack-lg">
          <Link className="font-headline-md text-xl sm:text-headline-md font-bold text-primary" href="/">SIIT Discover</Link>
          <nav className="hidden md:flex gap-stack-md">
            {[["Pathfinding", "/discover"], ["Libraries", "/targets"], ["Roadmaps", "/roadmap"], ["Skills", "/skills"]].map(([label, href]) => (
              <Link key={label} className={`${active === label ? "text-primary font-bold border-b-2 border-primary" : "text-secondary hover:text-primary"} transition-colors text-body-md pb-1`} href={href}>{label}</Link>
            ))}
          </nav>
        </div>
        <Link href="/portfolio" className="bg-primary text-on-primary px-4 py-2 rounded-lg text-sm sm:text-body-md hover:bg-primary-container transition-colors">เพิ่มผลงาน</Link>
      </div>
    </header>
  );
}

type WorkspaceActive = "workspace" | "quiz" | "portfolio" | "targets" | "roadmap" | "skills";

export function WorkspaceSidebar({ active, variant = "helpful" }: { active: WorkspaceActive; variant?: "helpful" | "graph" }) {
  const links: { id: WorkspaceActive; label: string; icon: string; href: string }[] = variant === "graph"
    ? [
        { id: "workspace", label: "My Workspace", icon: "grid_view", href: "/" },
        { id: "skills", label: "Skill Graph", icon: "hub", href: "/skills" },
        { id: "roadmap", label: "Roadmaps", icon: "route", href: "/roadmap" },
        { id: "targets", label: "Career Library", icon: "menu_book", href: "/targets" },
        { id: "portfolio", label: "Skill Extraction", icon: "psychology_alt", href: "/portfolio" },
      ]
    : [
        { id: "workspace", label: "Dashboard", icon: "dashboard", href: "/" },
        { id: "quiz", label: "Activity Quiz", icon: "quiz", href: "/discover" },
        { id: "portfolio", label: "Skill Extraction", icon: "psychology_alt", href: "/portfolio" },
        { id: "targets", label: "Career Library", icon: "menu_book", href: "/targets" },
        { id: "roadmap", label: "My Roadmap", icon: "route", href: "/roadmap" },
      ];
  return (
    <aside className="hidden lg:flex flex-col h-screen sticky top-0 p-stack-md bg-surface-muted border-r border-border-low w-64 z-40 shrink-0">
      <div className="mb-stack-lg flex items-center gap-3 px-3">
        <span className="w-10 h-10 rounded-lg bg-primary-fixed text-primary grid place-items-center"><Icon>{variant === "graph" ? "hub" : "route"}</Icon></span>
        <div><h2 className="font-headline-md text-lg font-bold text-on-surface">{variant === "graph" ? "SIIT Workspace" : "Helpful Senior"}</h2><p className="font-label-sm text-xs text-text-subtle">Career Workspace</p></div>
      </div>
      <Link href="/discover" className="mx-2 mb-stack-md bg-primary text-on-primary font-label-sm text-label-sm py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 hover:bg-primary-container transition-colors"><Icon className="text-sm">add</Icon> New Analysis</Link>
      <nav className="flex-1 flex flex-col gap-1 px-2">
        {links.map((item) => (
          <Link key={item.id} href={item.href} className={`flex items-center gap-3 px-4 py-2.5 rounded-lg font-label-sm text-label-sm transition-all ${active === item.id ? "bg-secondary-container text-primary font-bold" : "text-secondary hover:bg-surface-container"}`}><Icon>{item.icon}</Icon>{item.label}</Link>
        ))}
      </nav>
      <div className="mt-auto pt-4 border-t border-border-low px-2 flex flex-col gap-1">
        <Link className="flex items-center gap-3 px-4 py-2 rounded-lg text-secondary hover:bg-surface-container" href="/portfolio"><Icon>settings</Icon>Settings</Link>
        <Link className="flex items-center gap-3 px-4 py-2 rounded-lg text-secondary hover:bg-surface-container" href="/"><Icon>help</Icon>Support</Link>
      </div>
    </aside>
  );
}

export function MobileWorkspaceNav({ active }: { active: WorkspaceActive }) {
  const links = [
    ["workspace", "grid_view", "Home", "/"],
    ["skills", "hub", "Skills", "/skills"],
    ["roadmap", "route", "Roadmap", "/roadmap"],
    ["targets", "menu_book", "Library", "/targets"],
    ["portfolio", "person", "Profile", "/portfolio"],
  ];
  return (
    <nav className="fixed bottom-0 w-full z-50 lg:hidden rounded-t-xl border-t border-border-low bg-surface-bg shadow-lg no-print">
      <ul className="flex justify-around items-center px-2 py-2">
        {links.map(([id, icon, label, href]) => <li key={id}><Link className={`flex flex-col items-center justify-center min-w-14 p-2 rounded-xl ${active === id ? "bg-primary-container text-on-primary-container" : "text-text-subtle"}`} href={href}><Icon>{icon}</Icon><span className="text-[10px] mt-1">{label}</span></Link></li>)}
      </ul>
    </nav>
  );
}

export function SiteFooter({ discover = false }: { discover?: boolean }) {
  return (
    <footer className="bg-surface-muted border-t border-border-low w-full mt-auto">
      <div className="py-stack-lg px-gutter max-w-container-max mx-auto flex flex-col md:flex-row justify-between items-center gap-stack-md">
        <div className="font-headline-md text-xl sm:text-headline-md font-bold text-secondary">{discover ? "SIIT Discover" : "SIIT Roadmap"}</div>
        <nav className="flex flex-wrap justify-center gap-stack-md text-label-sm"><Link className="text-text-subtle hover:text-primary" href="/">Privacy Policy</Link><Link className="text-text-subtle hover:text-primary" href="/">Terms of Service</Link><Link className="text-text-subtle hover:text-primary" href="/">Contact</Link></nav>
        <p className="text-xs sm:text-sm text-text-subtle text-center">© 2026 SIIT Roadmap. Built for growth.</p>
      </div>
    </footer>
  );
}

export function InlineNotice({ children, tone = "info" }: { children: React.ReactNode; tone?: "info" | "error" | "success" }) {
  const cls = tone === "error" ? "bg-error-container text-on-error-container" : tone === "success" ? "bg-[#e8f5ed] text-[#275d3b]" : "bg-primary-fixed text-on-primary-fixed-variant";
  return <div role="status" className={`${cls} rounded-lg px-4 py-3 text-sm flex gap-2 items-start`}><Icon className="text-[18px]">{tone === "error" ? "error" : tone === "success" ? "check_circle" : "info"}</Icon><div>{children}</div></div>;
}
