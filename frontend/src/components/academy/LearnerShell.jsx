import { BarChart3, BookOpen, ChevronDown, Home, LifeBuoy, LogOut, Menu, Moon, Search, Settings, Sun, Ticket, Wrench, X } from "lucide-react";
import { createContext, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import ReportIssueButton from "../ReportIssueButton";
import { getStudentStats, globalSearch } from "../../services/api";
import AcademyScene from "./AcademyScene";
import "./academy.css";

// Today publishes its existing stats request; other routes can fetch account data.
export const LearnerStatsContext = createContext(() => {});
const icons = { Today: Home, "My Course": BookOpen, "Service Desk": Ticket, Progress: BarChart3, "Extra Practice": Wrench };

export default function LearnerShell({ children, isDark, setIsDark, student, items, onLogout, isActive }) {
  const location = useLocation();
  const [stats, setStats] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [practiceOpen, setPracticeOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchState, setSearchState] = useState({ lessons: [], commands: [], status: "idle" });
  const search = useRef(null);
  const accountButton = useRef(null);
  const account = useRef(null);
  const searchAnchor = useRef(null);
  const menu = useRef(null);
  const menuButton = useRef(null);
  const menuWasOpen = useRef(false);
  const brand = useRef(null);

  useEffect(() => {
    setMenuOpen(false); setAccountOpen(false); setSearchOpen(false); setQuery("");
  }, [location.pathname]);
  useEffect(() => {
    if (location.pathname === "/" || stats || !student?.id) return;
    let active = true;
    getStudentStats(student.id, { suppressToast: true }).then(res => { if (active) setStats(res.data); }).catch(() => {});
    return () => { active = false; };
  }, [student?.id, location.pathname, stats]);
  useEffect(() => {
    if (accountOpen) account.current?.querySelector("button")?.focus();
    if (menuOpen) menu.current?.querySelector("a,button")?.focus();
    else if (menuWasOpen.current) (window.matchMedia("(max-width: 767px)").matches ? menuButton : brand).current?.focus();
    menuWasOpen.current = menuOpen;
  }, [accountOpen, menuOpen]);
  useEffect(() => {
    const key = event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault(); setSearchOpen(true); setMenuOpen(false);
        requestAnimationFrame(() => search.current?.focus());
      }
      if (event.key === "Tab" && menuOpen) {
        const controls = [...menu.current.querySelectorAll("a,button,input")];
        const first = controls[0], last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
      if (event.key === "Escape") {
        if (accountOpen) accountButton.current?.focus();
        if (menuOpen) menuButton.current?.focus();
        setMenuOpen(false); setAccountOpen(false); setSearchOpen(false);
      }
    };
    const outside = event => {
      if (!account.current?.contains(event.target) && !accountButton.current?.contains(event.target)) setAccountOpen(false);
      if (!searchAnchor.current?.contains(event.target)) setSearchOpen(false);
    };
    document.addEventListener("keydown", key); document.addEventListener("pointerdown", outside);
    return () => { document.removeEventListener("keydown", key); document.removeEventListener("pointerdown", outside); };
  }, [accountOpen, menuOpen]);
  useEffect(() => {
    const narrow = window.matchMedia("(max-width: 767px)");
    let focusedMobileControl = false;
    const rememberFocus = event => {
      focusedMobileControl = event.target === menuButton.current || Boolean(menu.current?.contains(event.target));
    };
    const resize = () => { if (!narrow.matches) {
      setMenuOpen(false);
      if (focusedMobileControl) requestAnimationFrame(() => brand.current?.focus());
    } };
    document.addEventListener("focusin", rememberFocus);
    narrow.addEventListener?.("change", resize);
    return () => { narrow.removeEventListener?.("change", resize); document.removeEventListener("focusin", rememberFocus); };
  }, []);
  useEffect(() => {
    let active = true;
    if (!query.trim()) { setSearchState({ lessons: [], commands: [], status: "idle" }); return; }
    setSearchState({ lessons: [], commands: [], status: "loading" });
    const timer = setTimeout(() => {
      globalSearch(query.trim(), { suppressToast: true })
        .then(res => { if (active) setSearchState({ ...res.data, status: "ready" }); })
        .catch(() => { if (active) setSearchState({ lessons: [], commands: [], status: "error" }); });
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);

  function navigation(mobile = false) {
    return <nav className="nav" aria-label={mobile ? "All navigation" : "Primary navigation"}>
      {items.map(item => {
        const Icon = icons[item.label] || Home;
        if (item.children) return <div key={item.label}>
          <button type="button" className={`nav-settings ${isActive(item, location) ? "has-active-child" : ""}`} title={item.label} aria-label={item.label} aria-expanded={practiceOpen} aria-controls={mobile ? "academy-mobile-practice" : "academy-practice"} onClick={() => setPracticeOpen(!practiceOpen)}><Icon size={20} aria-hidden="true" /><span>{item.label}</span><ChevronDown className="nav-chevron" size={14} aria-hidden="true" /></button>
          {practiceOpen ? <div className="practice-links" id={mobile ? "academy-mobile-practice" : "academy-practice"}>{item.children.map(child => <Link key={child.to} to={child.to} aria-current={isActive(child, location) ? "page" : undefined}>{child.label}</Link>)}</div> : null}
        </div>;
        const props = { className: "nav-link", "aria-current": isActive(item, location) ? "page" : undefined, title: item.label, "aria-label": item.label };
        const content = <><Icon size={20} aria-hidden="true" /><span>{item.label}</span></>;
        return item.external ? <a key={item.to} href={item.to} {...props}>{content}</a> : <Link key={item.to} to={item.to} {...props}>{content}</Link>;
      })}
      <button type="button" className="nav-settings" onClick={() => setIsDark(!isDark)} aria-label="Theme settings" title="Theme settings"><Settings size={20} aria-hidden="true" /><span>Theme settings</span></button>
    </nav>;
  }

  return <LearnerStatsContext.Provider value={setStats}><div className={`academy ${isDark ? "dark" : "light"}`}>
    <a href="#learner-content" className="academy-skip">Skip to content</a>
    <aside className="sidebar" aria-label="Learner sidebar">
      <Link ref={brand} className="brand" to="/" aria-label="Nexus Academy home"><img className="brand-mark" src="/academy/nexus-mark.svg" alt="" /><span className="brand-name"><strong>NEXUS</strong><small>ACADEMY</small></span></Link>
      {navigation()}
      <div className="sidebar-support"><ReportIssueButton compact /></div>
      <div className="sidebar-art"><AcademyScene kind="sidebar" dark={isDark} /><p>“Discipline today,<br />stronger tomorrow.”</p></div>
    </aside>
    <div className={`academy-workspace ${location.pathname === "/" ? "academy-today-workspace" : ""}`}>
      <AcademyScene kind="footer" dark={isDark} />
      <header className="topbar" aria-hidden={menuOpen || undefined} inert={menuOpen ? "" : undefined}>
        <div className="mobile-brand">NEXUS ACADEMY</div>
        <div className="search-wrap" ref={searchAnchor}>
          <label className="search"><Search size={20} aria-hidden="true" /><input ref={search} type="search" aria-label="Search lessons or commands" placeholder="Search lessons or commands…" value={query} onFocus={() => setSearchOpen(true)} onChange={e => setQuery(e.target.value)} /><kbd>Ctrl K</kbd></label>
          {searchOpen && query.trim() ? <div className="search-results" role="region" aria-label="Search results">
            {searchState.status === "loading" ? <p role="status">Searching…</p> : searchState.status === "error" ? <p role="alert">Search is unavailable. Try again shortly.</p> : <>
              {(searchState.lessons || []).map(lesson => <Link key={lesson.id} to={`/lessons/${lesson.id}`}>{lesson.title}</Link>)}
              {(searchState.commands || []).map(command => <Link key={command.id} to="/commands">{command.command}</Link>)}
              {!searchState.lessons?.length && !searchState.commands?.length ? <p>No matches found.</p> : null}
            </>}
          </div> : null}
        </div>
        <div className="account">
          <button className="iconbtn" onClick={() => setIsDark(!isDark)} aria-label="Toggle dark mode" aria-pressed={isDark} type="button">{isDark ? <Sun size={19} aria-hidden="true" /> : <Moon size={19} aria-hidden="true" />}</button>
          <div className="header-support"><ReportIssueButton compact /></div>
          {stats && (stats.level_name || Number.isFinite(stats.total_xp)) ? <div className="rank"><strong>{stats.level_name ? `${Number.isFinite(stats.level) ? `Level ${stats.level} · ` : ""}${stats.level_name}` : student?.name}</strong>{Number.isFinite(stats.total_xp) ? <span>{stats.total_xp.toLocaleString()} XP</span> : null}</div> : null}
          <div className="account-anchor">
            <button ref={accountButton} className="avatar" type="button" aria-label="Account menu" aria-expanded={accountOpen} aria-controls={accountOpen ? "academy-account" : undefined} onClick={() => { setAccountOpen(!accountOpen); setSearchOpen(false); setMenuOpen(false); }}><img src="/academy/hooded-wanderer.webp" alt="" /></button>
            {accountOpen ? <div ref={account} id="academy-account" className="account-panel" role="group" aria-label="Account actions"><p className="muted small">Signed in as</p><strong>{student?.name}</strong><button className="btn btn-secondary" onClick={onLogout} type="button"><LogOut size={16} aria-hidden="true" />Sign out</button></div> : null}
          </div>
          <button ref={menuButton} className="iconbtn learner-menu-toggle" type="button" aria-label="Toggle menu" aria-expanded={menuOpen} aria-controls={menuOpen ? "academy-mobile-menu" : undefined} onClick={() => { setMenuOpen(!menuOpen); setAccountOpen(false); }}><Menu size={20} aria-hidden="true" /></button>
        </div>
      </header>
      {menuOpen ? <><button type="button" className="learner-menu-backdrop" aria-label="Close navigation" onClick={() => { setMenuOpen(false); menuButton.current?.focus(); }} /><div ref={menu} id="academy-mobile-menu" className="learner-mobile-menu" role="dialog" aria-modal="true" aria-label="Learner navigation"><div className="section-title"><strong>Navigation</strong><button className="iconbtn" type="button" aria-label="Close menu" onClick={() => { setMenuOpen(false); menuButton.current?.focus(); }}><X size={20} aria-hidden="true" /></button></div>{navigation(true)}<ReportIssueButton /></div></> : null}
      <div id="learner-content" tabIndex={-1} className="academy-content" aria-hidden={menuOpen || undefined} inert={menuOpen ? "" : undefined}>{children}</div>
    </div>
    <nav className="mobile-nav" aria-label="Mobile primary navigation" aria-hidden={menuOpen || undefined} inert={menuOpen ? "" : undefined}>{items.map(item => {
      const target = item.children?.[0] || item;
      const Icon = icons[item.label] || LifeBuoy;
      const props = { "aria-label": item.label, "aria-current": isActive(item, location) ? "page" : undefined };
      const content = <><Icon size={20} aria-hidden="true" /><span>{item.label === "Extra Practice" ? "Practice" : item.label === "My Course" ? "Course" : item.label === "Service Desk" ? "Desk" : item.label}</span></>;
      return target.external ? <a href={target.to} key={item.label} {...props}>{content}</a> : <Link to={target.to} key={item.label} {...props}>{content}</Link>;
    })}</nav>
  </div></LearnerStatsContext.Provider>;
}
