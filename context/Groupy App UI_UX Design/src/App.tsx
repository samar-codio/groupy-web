import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

type Screen = "dashboard" | "todo" | "group" | "calendar" | "day" | "task" | "request" | "add" | "create" | "join" | "files" | "notifs" | "feedback" | "settings";
type Group = { id: number; name: string; sub: string; unread: number; alt: boolean; code: string; admin: boolean; demo: boolean; members: number };
type Tab = "history" | "tasks" | "people" | "requests";
type Ev = { id: number; date: string; title: string; group: string; color?: number };

const I = ({ children, size = 22 }: { children: ReactNode; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    {children}
  </svg>
);

const Ic = {
  menu: <I><path d="M4 6h16M4 12h16M4 18h16" /></I>,
  dots: <I><circle cx="12" cy="5" r="1.3" fill="currentColor" /><circle cx="12" cy="12" r="1.3" fill="currentColor" /><circle cx="12" cy="19" r="1.3" fill="currentColor" /></I>,
  back: <I><path d="M19 12H5M11 6l-6 6 6 6" /></I>,
  close: <I><path d="M6 6l12 12M18 6L6 18" /></I>,
  plus: <I><path d="M12 5v14M5 12h14" /></I>,
  squarePlus: <I><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M12 8v8M8 12h8" /></I>,
  login: <I><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 8l4 4-4 4M14 12H3" /></I>,
  logout: <I><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 8l4 4-4 4M20 12H9" /></I>,
  groups: <I><circle cx="9" cy="8" r="3" /><path d="M3 20c0-3.3 2.700-6 6-6s6 2.700 6 6" /><path d="M16 5.500a3 3 0 0 1 0 5.500M18 14.500c1.800.8 3 2.600 3 5.500" /></I>,
  calendar: <I><rect x="3.500" y="5" width="17" height="15" rx="2" /><path d="M3.500 10h17M8 3v4M16 3v4" /></I>,
  folder: <I><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></I>,
  bell: <I><path d="M6 17V11a6 6 0 1 1 12 0v6l1.500 2h-15zM10 21h4" /></I>,
  feedback: <I><path d="M4 5h16v11H9l-5 4z" /></I>,
  settings: <I><circle cx="12" cy="12" r="3" /><path d="M12 2.500v3M12 18.500v3M2.500 12h3M18.500 12h3M5.300 5.300l2.100 2.100M16.600 16.600l2.100 2.100M5.300 18.700l2.100-2.100M16.600 7.400l2.100-2.100" /></I>,
  user: <I><circle cx="12" cy="8.500" r="3.500" /><path d="M5 20c0-3.900 3.100-7 7-7s7 3.100 7 7" /></I>,
  clipboard: <I><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4.500h6V3H9zM9 11h6M9 15h4" /></I>,
  chat: <I><path d="M4 5h12v9H8l-4 3.500zM9 17.500h7l4 3V10h-3" /></I>,
  megaphone: <I><path d="M4 10v4l12 5V5zM16 9a3 3 0 0 1 0 6M7 15v4" /></I>,
  pencil: <I><path d="M4 20l1-4L16.500 4.500a2 2 0 0 1 3 3L8 19z" /></I>,
  chevron: <I><path d="M6 9l6 6 6-6" /></I>,
  left: <I><path d="M15 6l-6 6 6 6" /></I>,
  right: <I><path d="M9 6l6 6-6 6" /></I>,
  refresh: <I><path d="M20 12a8 8 0 1 1-2.500-5.800M20 4v5h-5" /></I>,
  moon: <I><path d="M20 14.500A8 8 0 0 1 9.500 4a8 8 0 1 0 10.500 10.500z" /></I>,
  search: <I><circle cx="11" cy="11" r="6.500" /><path d="M16 16l4.500 4.500" /></I>,
  file: <I><path d="M6 3h8l4 4v14H6zM14 3v4h4M9 13h6M9 17h4" /></I>,
  image: <I><rect x="3.500" y="4.500" width="17" height="15" rx="2" /><circle cx="9" cy="10" r="1.600" /><path d="M4 18l5-5 4 4 3-3 4 4" /></I>,
  zip: <I><path d="M6 3h8l4 4v14H6zM14 3v4h4M11 9h2M11 12h2M11 15h2" /></I>,
  clock: <I><circle cx="12" cy="12" r="8.500" /><path d="M12 7v5l3 2" /></I>,
  target: <I><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.800" fill="currentColor" /></I>,
  details: <I><path d="M4 7h16M4 12h16M4 17h10" /></I>,
  clip: <I><path d="M20 11l-8.500 8.500a5 5 0 0 1-7-7L13 4a3.500 3.500 0 0 1 5 5l-8.500 8.500a2 2 0 0 1-3-3L14 7" /></I>,
  camera: <I><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.500" /></I>,
  download: <I><path d="M12 4v11M7 11l5 5 5-5M5 20h14" /></I>,
  check: <I><path d="M5 12.500l4.500 4.500L19 7.500" /></I>,
  copy: <I size={16}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h8" /></I>,
  backspace: <I><path d="M9 5h10a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H9l-6-7zM12 9.500l4 5M16 9.500l-4 5" /></I>,
  palette: <I><path d="M12 3a9 9 0 1 0 0 18c1.400 0 2-.9 2-1.800 0-1.200-1-1.500-1-2.700 0-1 .8-1.500 1.800-1.500H17a4 4 0 0 0 4-4C21 6.500 17 3 12 3z" /><circle cx="7.500" cy="11" r="1" fill="currentColor" /><circle cx="10.500" cy="7.500" r="1" fill="currentColor" /><circle cx="15" cy="7.500" r="1" fill="currentColor" /></I>,
  filter: <I><path d="M4 6h16M7 12h10M10 18h4" /></I>,
};

function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" aria-label="Groupy logo">
      <rect width="512" height="512" rx="112" fill="var(--accent)" />
      <g stroke="var(--bg)" strokeWidth="18" strokeLinecap="round"><path d="M256 256V112M256 256V400M256 256H112M256 256H400" /></g>
      <g fill="var(--bg)">
        <circle cx="256" cy="256" r="54" />
        <circle cx="256" cy="108" r="32" />
        <circle cx="256" cy="404" r="32" />
        <circle cx="108" cy="256" r="32" />
        <circle cx="404" cy="256" r="32" />
      </g>
    </svg>
  );
}

function Shapes() {
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 130" preserveAspectRatio="xMaxYMid slice" aria-hidden>
      <path d="M170 0h150v130H210c-40 0-30-45-5-60 25-14 15-45-35-70z" fill="#fff" opacity="0.1" />
      <circle cx="262" cy="34" r="22" fill="#fff" opacity="0.14" />
      <circle cx="226" cy="98" r="14" fill="#fff" opacity="0.1" />
      <rect x="250" y="64" width="46" height="60" rx="5" transform="rotate(14 273 94)" fill="#fff" opacity="0.14" />
      <g fill="#fff" opacity="0.25">
        {Array.from({ length: 24 }).map((_, i) => (
          <circle key={i} cx={10 + (i % 6) * 8} cy={90 + Math.floor(i / 6) * 8} r="1.200" />
        ))}
      </g>
    </svg>
  );
}

const initialGroups: Group[] = [
  { id: 1, name: "CN 5E Fall 2026", sub: "Computer Networks", unread: 4, alt: false, code: "CN5E26", admin: true, demo: true, members: 38 },
  { id: 2, name: "Technical & Business Writing", sub: "CS-5E", unread: 12, alt: true, code: "TBW5E7", admin: false, demo: true, members: 41 },
  { id: 3, name: "Computer Architecture", sub: "BCS-5E · Mon 11:45 · Tue 10:00", unread: 7, alt: false, code: "CA5E88", admin: false, demo: true, members: 36 },
  { id: 4, name: "Applied Human Computer Interaction", sub: "BCS-5E", unread: 3, alt: true, code: "HCI5E3", admin: false, demo: true, members: 33 },
];
const directory = [
  { code: "OS5E26", name: "Operating Systems", sub: "BCS-5E", members: 40 },
  { code: "SE5E26", name: "Software Engineering", sub: "BCS-5E", members: 35 },
];
const PERSONAL = "Personal tasks";
const PALETTE = ["#587457", "#c0734f", "#4f84ad", "#a8588f", "#a8832a", "#7061b3", "#2f8f8b", "#bd4b4b"];
const genCode = () => Array.from({ length: 6 }, () => "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[Math.floor(Math.random() * 32)]).join("");

type GTask = { id: number; gid: number; title: string; date: string; allDay: boolean; start: string; end: string; repeat: string; deadline: string; details: string; posted: string };
const initialTasks: GTask[] = [
  { id: 1, gid: 1, title: "Assignment 2: Transport Layer", date: "2026-10-13", allDay: true, start: "09:00", end: "10:00", repeat: "Does not repeat", deadline: "2026-10-16", details: "Solve all problems from Chapter 3 (TCP flow control and congestion control). Submit a single PDF on the portal before the deadline.", posted: "9:40 AM" },
  { id: 2, gid: 1, title: "Assignment 1", date: "2026-09-22", allDay: true, start: "09:00", end: "10:00", repeat: "Does not repeat", deadline: "2026-10-09", details: "Network layer subnetting worksheet. Show your working for every question.", posted: "Sep 22" },
  { id: 3, gid: 1, title: "Quiz 1 Preparation", date: "2026-09-30", allDay: false, start: "09:00", end: "10:30", repeat: "Every week", deadline: "2026-10-05", details: "Revise Chapters 1 and 2. Quiz covers layered architecture and application-layer protocols.", posted: "Sep 30" },
];
type Req = GTask & { by: string };
const initialRequests: Req[] = [
  { id: 101, gid: 1, by: "Hira Siddiqui", title: "Lab 3: Wireshark Packet Capture", date: "2026-10-13", allDay: true, start: "09:00", end: "10:00", repeat: "Does not repeat", deadline: "2026-10-20", details: "Capture and analyse a TCP three-way handshake using Wireshark. Submit the .pcap file and a one-page summary.", posted: "10:15 AM" },
  { id: 102, gid: 1, by: "Bilal Ahmed", title: "Group Presentation Slot Sign-up", date: "2026-10-14", allDay: false, start: "11:00", end: "12:00", repeat: "Every week", deadline: "2026-10-18", details: "Teams should pick their presentation slot before Sunday so the schedule can be shared.", posted: "Yesterday" },
];
const shortDate = (k: string) => new Date(k + "T00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });

const todoSections = [
  { label: "No due date", items: [] as { title: string; subject: string; due: string }[] },
  { label: "This week", items: [
    { title: "Assignment 2: Transport Layer", subject: "CN 5E Fall 2026", due: "Fri, 11:59 PM" },
    { title: "Cache Memory Worksheet", subject: "Computer Architecture", due: "Sat, 5:00 PM" },
  ] },
  { label: "Next week", items: [{ title: "Usability Study Report", subject: "Applied Human Computer Interaction", due: "Oct 22, 9:00 AM" }] },
  { label: "Later", items: [{ title: "Technical Report Draft", subject: "Technical & Business Writing", due: "Nov 12, 11:59 PM" }] },
];

const files = [
  { name: "Chapter 4 - Network Layer.pdf", group: "CN 5E Fall 2026", date: "Oct 14, 2:30 PM", type: "pdf", size: "4.2 MB", by: "Umar Aftab" },
  { name: "Transport_Layer_Slides.pdf", group: "CN 5E Fall 2026", date: "Oct 16", type: "pdf", size: "2.8 MB", by: "Umar Aftab" },
  { name: "Cache Memory Notes", group: "Computer Architecture", date: "Oct 12, 10:05 AM", type: "folder", size: "6 items", by: "Hira Siddiqui" },
  { name: "Whiteboard Photos - Lecture 7.jpg", group: "Computer Architecture", date: "Oct 11", type: "image", size: "1.9 MB", by: "Bilal Ahmed" },
  { name: "Report Template.docx", group: "Technical & Business Writing", date: "Oct 9, 4:40 PM", type: "doc", size: "310 KB", by: "Ayesha Khan" },
  { name: "HCI Past Papers.zip", group: "Applied Human Computer Interaction", date: "Oct 6", type: "zip", size: "18.4 MB", by: "Zain Malik" },
  { name: "computer-networking-a-top-down-approach.pdf", group: "CN 5E Fall 2026", date: "Sep 28", type: "pdf", size: "24.1 MB", by: "Umar Aftab" },
];
const fileIcon = (t: string) => (t === "folder" ? Ic.folder : t === "image" ? Ic.image : t === "zip" ? Ic.zip : Ic.file);

const initialNotifs = [
  { id: 1, kind: "task", text: "New task assigned: Final Project Proposal", group: "Technical & Business Writing", time: "9:15 AM", unread: true },
  { id: 2, kind: "announce", text: "Umar Aftab posted a new announcement", group: "Computer Architecture", time: "10:00 AM", unread: true },
  { id: 3, kind: "chat", text: "Hira Siddiqui: Can someone share the lab manual?", group: "CN 5E Fall 2026", time: "Yesterday", unread: true },
  { id: 4, kind: "task", text: "Due tomorrow: Assignment 2: Transport Layer", group: "CN 5E Fall 2026", time: "Yesterday", unread: false },
  { id: 5, kind: "announce", text: "Quiz 2 moved to Thursday", group: "Applied Human Computer Interaction", time: "Mon", unread: false },
  { id: 6, kind: "chat", text: "Bilal Ahmed uploaded Whiteboard Photos", group: "Computer Architecture", time: "Sun", unread: false },
];
const notifIcon = (k: string) => (k === "task" ? Ic.clipboard : k === "chat" ? Ic.chat : Ic.megaphone);

const initialEvents: Ev[] = [
  { id: 1, date: "2026-10-02", title: "Task 1", group: "CN 5E Fall 2026" },
  { id: 2, date: "2026-10-09", title: "Assignment 1", group: "CN 5E Fall 2026" },
  { id: 3, date: "2026-10-14", title: "Task 1", group: "Computer Architecture" },
  { id: 4, date: "2026-10-16", title: "Assignment 2", group: "CN 5E Fall 2026" },
  { id: 5, date: "2026-10-20", title: "Presentation", group: "Technical & Business Writing" },
  { id: 6, date: "2026-10-20", title: "Quiz Due", group: "Computer Architecture" },
  { id: 7, date: "2026-10-22", title: "Quiz Due", group: "Applied Human Computer Interaction" },
  { id: 8, date: "2026-10-27", title: "Lab Report", group: "CN 5E Fall 2026" },
  { id: 9, date: "2026-10-29", title: "Task 2", group: "Technical & Business Writing" },
  { id: 10, date: "2026-11-12", title: "Report Draft", group: "Technical & Business Writing" },
  { id: 11, date: "2026-10-13", title: "Buy lab coat", group: PERSONAL },
  { id: 12, date: "2026-10-17", title: "Revise for midterms", group: PERSONAL },
];

const TODAY = "2026-10-13";
const key = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const fmtDate = (k: string) => new Date(k + "T00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });

const LS = {
  get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  del: (k: string) => { try { localStorage.removeItem(k); } catch { /* storage unavailable */ } },
};
const sha = async (s: string) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)))).map((b) => b.toString(16).padStart(2, "0")).join("");
type Account = { email: string; pwHash: string };
const readAccount = (): Account | null => { try { return JSON.parse(LS.get("groupy.account") ?? "null"); } catch { return null; } };

const inputCls = "h-11 w-full rounded-md border border-line bg-bg px-3 text-[15px] outline-none placeholder:text-muted focus:border-primary";
const CODE_LEN = 6;

function CodePad({ title, hint, onSubmit }: { title: string; hint: ReactNode; onSubmit: (code: string) => string | void }) {
  const [digits, setDigits] = useState("");
  const [err, setErr] = useState("");
  const [shake, setShake] = useState(0);
  const press = (d: string) => { setErr(""); setDigits((p) => (p.length < CODE_LEN ? p + d : p)); };
  const back = () => setDigits((p) => p.slice(0, -1));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) press(e.key);
      else if (e.key === "Backspace") back();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (digits.length !== CODE_LEN) return;
    const r = onSubmit(digits);
    if (r) { setErr(r); setShake((n) => n + 1); }
    setDigits("");
  }, [digits]);

  return (
    <div className="text-center">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-muted">{hint}</p>
      <div key={shake} className="mt-5 flex justify-center gap-2" style={shake ? { animation: "shake .35s" } : undefined}>
        {Array.from({ length: CODE_LEN }).map((_, i) => (
          <span key={i} className={`grid h-12 w-10 place-items-center rounded-md border text-xl font-semibold ${i < digits.length ? "border-primary bg-primary/10" : "border-line bg-bg"}`}>{digits[i] ?? ""}</span>
        ))}
      </div>
      <p className="mt-3 h-5 text-sm text-danger" role="alert">{err}</p>
      <div className="mx-auto mt-3 grid max-w-[15rem] grid-cols-3 gap-2">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
          <button key={d} type="button" onClick={() => press(d)} className="h-12 rounded-md border border-line bg-bg text-lg font-medium transition hover:border-primary active:scale-95">{d}</button>
        ))}
        <span />
        <button type="button" onClick={() => press("0")} className="h-12 rounded-md border border-line bg-bg text-lg font-medium transition hover:border-primary active:scale-95">0</button>
        <button type="button" aria-label="Delete digit" onClick={back} className="grid h-12 place-items-center rounded-md text-muted transition hover:bg-line/50 active:scale-95">{Ic.backspace}</button>
      </div>
    </div>
  );
}

function AuthFlow({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = useState<"login" | "signup">("login");
  const [step, setStep] = useState<"form" | "otp">("form");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Account | null>(null);
  const [code, setCode] = useState("");
  const [sentAt, setSentAt] = useState(0);
  const [resent, setResent] = useState(false);

  const switchKind = (m: "login" | "signup") => { setKind(m); setErr(""); setPw(""); setPw2(""); };
  const sendCode = () => {
    setCode(String(crypto.getRandomValues(new Uint32Array(1))[0] % 1000000).padStart(CODE_LEN, "0"));
    setSentAt(Date.now());
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    const em = email.trim().toLowerCase();
    if (!/^\S+@\S+\.\S+$/.test(em)) return setErr("Enter a valid email address.");
    if (pw.length < 6) return setErr("Password must be at least 6 characters.");
    if (kind === "signup" && pw !== pw2) return setErr("Passwords do not match.");
    setBusy(true);
    const pwHash = await sha(em + ":" + pw);
    setBusy(false);
    if (kind === "login") {
      const acc = readAccount();
      if (!acc || acc.email !== em) return setErr("No account found for this email. Sign up first.");
      if (acc.pwHash !== pwHash) return setErr("Incorrect password.");
    }
    setPending({ email: em, pwHash });
    sendCode();
    setResent(false);
    setStep("otp");
  };

  const verify = (entered: string) => {
    if (!pending) return;
    if (Date.now() - sentAt > 5 * 60 * 1000) return "This code has expired. Request a new one.";
    if (entered !== code) return "Incorrect code. Try again.";
    if (kind === "signup") LS.set("groupy.account", JSON.stringify(pending));
    LS.set("groupy.session", "1");
    onDone();
  };

  return (
    <div className="flex min-h-full items-center justify-center overflow-y-auto bg-bg px-4 py-8">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <Logo size={48} />
          <h1 className="text-2xl font-semibold tracking-tight">Groupy</h1>
          <p className="text-sm text-muted">Your class, organised in one place.</p>
        </div>
        <div className="rounded-lg border border-line border-l-[3px] border-l-primary bg-surface p-5">
          {step === "otp" ? (
            <>
              <CodePad
                title="Check your email"
                hint={<>We sent a {CODE_LEN}-digit code to <span className="font-medium text-ink">{pending?.email}</span>. It expires in 5 minutes.</>}
                onSubmit={verify}
              />
              <div className="mt-4 rounded-md border border-dashed border-line bg-bg px-3 py-2 text-center text-xs text-muted">
                Demo mode: no email server is connected, so the code is shown here: <span className="font-mono text-sm font-semibold tracking-widest text-ink">{code}</span>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm font-medium text-accent">
                <button onClick={() => { setStep("form"); setErr(""); }} className="hover:underline">Back</button>
                <button onClick={() => { sendCode(); setResent(true); }} className="hover:underline">{resent ? "Code resent" : "Resend code"}</button>
              </div>
            </>
          ) : (
            <>
              <div className="mb-5 grid grid-cols-2 rounded-md border border-line bg-bg p-0.5 text-sm font-semibold">
                {(["login", "signup"] as const).map((m) => (
                  <button key={m} type="button" onClick={() => switchKind(m)} className={`h-9 rounded-[5px] transition ${kind === m ? "bg-primary text-on-primary" : "text-muted"}`}>{m === "login" ? "Log in" : "Sign up"}</button>
                ))}
              </div>
              <form onSubmit={submit} className="space-y-4" noValidate>
                <label className="block">
                  <span className="mb-1.5 block text-sm font-medium">Email</span>
                  <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@university.edu" className={inputCls} />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-sm font-medium">Password</span>
                  <input type="password" autoComplete={kind === "signup" ? "new-password" : "current-password"} value={pw} onChange={(e) => setPw(e.target.value)} placeholder="At least 6 characters" className={inputCls} />
                </label>
                {kind === "signup" && (
                  <label className="block">
                    <span className="mb-1.5 block text-sm font-medium">Confirm password</span>
                    <input type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} placeholder="Repeat password" className={inputCls} />
                  </label>
                )}
                {err && <p className="text-sm text-danger" role="alert">{err}</p>}
                <button type="submit" disabled={busy || !email || !pw} className="h-11 w-full rounded-md bg-primary text-[15px] font-semibold text-on-primary transition enabled:hover:brightness-105 disabled:opacity-40">
                  Send verification code
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function IconBtn({ children, label, onClick, className = "" }: { children: ReactNode; label: string; onClick?: () => void; className?: string }) {
  return (
    <button aria-label={label} onClick={onClick} className={`grid h-10 w-10 shrink-0 place-items-center rounded-md text-ink transition hover:bg-line/60 active:scale-95 ${className}`}>
      {children}
    </button>
  );
}

function Modal({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center">
      <div className="absolute inset-0" style={{ background: "var(--scrim)", animation: "fade .2s" }} onClick={onClose} />
      <div className="relative w-full rounded-t-lg border border-line bg-surface px-3 pb-6 pt-3 md:max-w-md md:rounded-lg md:p-5" style={{ animation: "slide-up .25s ease-out" }}>
        <div className="mx-auto mb-3 h-1 w-10 rounded-sm bg-line md:hidden" />
        {children}
      </div>
    </div>
  );
}

function Empty({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-6 py-10 text-center">
      <span className="mx-auto grid h-12 w-12 place-items-center rounded-md bg-primary/15 text-accent">{icon}</span>
      <p className="mt-3 font-medium">{title}</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted">{text}</p>
    </div>
  );
}

const card = "rounded-lg border border-line border-l-[3px] border-l-primary bg-surface";

export default function App() {
  const [authed, setAuthed] = useState(() => LS.get("groupy.session") === "1" && !!readAccount());
  const [dark, setDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [tab, setTab] = useState<Tab>("history");
  const [sheet, setSheet] = useState(false);
  const [filterSheet, setFilterSheet] = useState(false);
  const [pop, setPop] = useState<null | "menu" | "profile">(null);
  const [open, setOpen] = useState<string[]>(["This week"]);
  const [toast, setToast] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [fileSel, setFileSel] = useState<(typeof files)[number] | null>(null);
  const [notifs, setNotifs] = useState(initialNotifs);
  const [events, setEvents] = useState(initialEvents);
  const [month, setMonth] = useState({ y: 2026, m: 9 });
  const [hidden, setHidden] = useState<string[]>([]);
  const [selDate, setSelDate] = useState(TODAY);
  const [calView, setCalView] = useState<"group" | "personal">("group");
  const [colorSheet, setColorSheet] = useState(false);
  const [groupColors, setGroupColors] = useState<Record<string, number>>({ [PERSONAL]: 1 });
  const [addCtx, setAddCtx] = useState<{ from: Screen; group: string | null; gid: number }>({ from: "calendar", group: null, gid: 0 });
  const [tasks, setTasks] = useState(initialTasks);
  const [taskId, setTaskId] = useState(0);
  const [requests, setRequests] = useState(initialRequests);
  const [reqId, setReqId] = useState(0);
  const [editGroup, setEditGroup] = useState<{ name: string; sub: string } | null>(null);
  const [form, setForm] = useState({ color: 1, title: "", date: TODAY, allDay: true, start: "09:00", end: "10:00", repeat: "Does not repeat", deadline: "", details: "" });
  const [fbText, setFbText] = useState("");
  const [fbFile, setFbFile] = useState("");
  const [fbSent, setFbSent] = useState(false);
  const [groupList, setGroupList] = useState(initialGroups);
  const [gid, setGid] = useState(1);
  const [cg, setCg] = useState({ title: "", sub: "" });
  const [joinCode, setJoinCode] = useState("");
  const [joinErr, setJoinErr] = useState("");
  const [avatar, setAvatar] = useState<string | null>(() => LS.get("groupy.avatar"));
  const touchX = useRef(0);
  const avatarInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#18221c" : "#f7f5ef");
  }, [dark]);

  const g = groupList.find((x) => x.id === gid) ?? groupList[0];
  const gTasks = tasks.filter((t) => t.gid === g.id);
  const task = tasks.find((t) => t.id === taskId);
  const req = requests.find((r) => r.id === reqId);
  const gReqs = requests.filter((r) => r.gid === g.id);
  const addAdmin = groupList.find((x) => x.id === addCtx.gid)?.admin ?? true;
  const approve = (r: Req) => {
    const { by: _by, ...t } = r;
    const name = groupList.find((x) => x.id === r.gid)?.name ?? "";
    setRequests((l) => l.filter((x) => x.id !== r.id));
    setTasks((l) => [{ ...t, posted: "Just now" }, ...l]);
    setEvents((l) => [...l, { id: Date.now(), date: r.date, title: r.title, group: name }]);
    flash("Task approved");
    if (screen === "request") go("group");
  };
  const decline = (r: Req) => {
    setRequests((l) => l.filter((x) => x.id !== r.id));
    flash("Request declined");
    if (screen === "request") go("group");
  };
  const email = readAccount()?.email ?? "";

  const flash = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(""), 1600);
  };
  const refresh = () => {
    setPop(null);
    flash("Refreshing…");
    setTimeout(() => window.location.reload(), 600);
  };
  const go = (s: Screen) => {
    setScreen(s);
    setPop(null);
    setSearchOpen(false);
    setQuery("");
    if (s === "feedback") setFbSent(false);
    if (s === "create") setCg({ title: "", sub: "" });
    if (s === "join") { setJoinCode(""); setJoinErr(""); }
  };
  const openAdd = (date = TODAY, group: string | null = null) => {
    setForm({ color: groupColors[PERSONAL] ?? 1, title: "", date, allDay: true, start: "09:00", end: "10:00", repeat: "Does not repeat", deadline: "", details: "" });
    setAddCtx({ from: screen, group, gid: group ? g.id : 0 });
    go("add");
  };
  const shiftMonth = (d: number) => setMonth(({ y, m }) => { const n = new Date(y, m + d, 1); return { y: n.getFullYear(), m: n.getMonth() }; });
  const openGroup = (id: number) => { setGid(id); setTab("history"); go("group"); };

  const createGroup = () => {
    const ng: Group = { id: Date.now(), name: cg.title.trim(), sub: cg.sub.trim() || "No description", unread: 0, alt: groupList.length % 2 === 1, code: genCode(), admin: true, demo: false, members: 1 };
    setGroupList((l) => [...l, ng]);
    openGroup(ng.id);
    flash("Group created");
  };
  const joinGroup = () => {
    const code = joinCode.trim().toUpperCase();
    const existing = groupList.find((x) => x.code === code);
    if (existing) { setJoinErr(`You are already a member of ${existing.name}.`); return; }
    const found = directory.find((d) => d.code === code);
    if (!found) { setJoinErr("No group found with that code. Check it with your CR and try again."); return; }
    const ng: Group = { id: Date.now(), name: found.name, sub: found.sub, unread: 0, alt: groupList.length % 2 === 1, code, admin: false, demo: false, members: found.members };
    setGroupList((l) => [...l, ng]);
    openGroup(ng.id);
    flash("Joined group");
  };
  const copyCode = () => {
    navigator.clipboard?.writeText(g.code).catch(() => {});
    flash("Group code copied");
  };

  const pickAvatar = (f?: File) => {
    if (!f || !f.type.startsWith("image/")) return;
    const r = new FileReader();
    r.onload = () => {
      const img = new Image();
      img.onload = () => {
        const size = 256;
        const c = document.createElement("canvas");
        c.width = c.height = size;
        const m = Math.min(img.width, img.height);
        c.getContext("2d")?.drawImage(img, (img.width - m) / 2, (img.height - m) / 2, m, m, 0, 0, size, size);
        const url = c.toDataURL("image/jpeg", 0.85);
        setAvatar(url);
        LS.set("groupy.avatar", url);
        flash("Profile picture updated");
      };
      img.src = r.result as string;
    };
    r.readAsDataURL(f);
  };
  const logout = () => {
    LS.del("groupy.session");
    setPop(null);
    setScreen("dashboard");
    setAuthed(false);
  };

  const cells = useMemo(() => {
    const first = new Date(month.y, month.m, 1);
    const start = new Date(month.y, month.m, 1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  }, [month]);

  const searchable = screen === "files" || screen === "notifs";
  const q = query.trim().toLowerCase();
  const unreadCount = notifs.filter((n) => n.unread).length;
  const filterNames = groupList.map((x) => x.name);
  const colorOf = (e: Ev) => PALETTE[(e.group === PERSONAL ? e.color ?? groupColors[PERSONAL] ?? 1 : groupColors[e.group] ?? Math.max(0, groupList.findIndex((x) => x.name === e.group))) % PALETTE.length];
  const ModeToggle = () => (
    <div className="grid grid-cols-2 rounded-md border border-line bg-bg p-0.5 text-xs font-semibold" role="group" aria-label="Calendar view">
      {(["group", "personal"] as const).map((m) => (
        <button key={m} aria-pressed={calView === m} onClick={() => setCalView(m)} className={`h-7 rounded-[5px] px-3 capitalize transition ${calView === m ? "bg-primary text-on-primary" : "text-muted"}`}>{m}</button>
      ))}
    </div>
  );
  const Swatches = ({ value, onPick }: { value: number; onPick: (i: number) => void }) => (
    <div className="flex flex-wrap gap-2">
      {PALETTE.map((c, i) => (
        <button key={c} type="button" aria-label={`Colour ${i + 1}`} aria-pressed={value % PALETTE.length === i} onClick={() => onPick(i)} style={{ background: c }} className={`grid h-7 w-7 place-items-center rounded-md text-white transition active:scale-90 ${value % PALETTE.length === i ? "ring-2 ring-ink ring-offset-2 ring-offset-surface" : ""}`}>
          {value % PALETTE.length === i && <I size={14}><path d="M5 12.500l4.500 4.500L19 7.500" /></I>}
        </button>
      ))}
    </div>
  );
  const hideNav = ["add", "create", "join"].includes(screen);

  const navActive: Record<string, boolean> = {
    Groups: ["dashboard", "group", "task", "request", "todo", "create", "join"].includes(screen),
    Calendar: ["calendar", "day", "add"].includes(screen),
    "Shared files": screen === "files",
    Notifications: screen === "notifs",
    Settings: screen === "settings" || screen === "feedback",
  };
  const top = [
    { label: "Groups", icon: Ic.groups, to: "dashboard" as Screen },
    { label: "Calendar", icon: Ic.calendar, to: "calendar" as Screen },
    { label: "Shared files", icon: Ic.folder, to: "files" as Screen },
    { label: "Notifications", icon: Ic.bell, to: "notifs" as Screen, count: 27 },
  ];
  const bottom = [{ label: "Settings", icon: Ic.settings, to: "settings" as Screen }];

  const NavList = ({ labelCls }: { labelCls: string }) => {
    const row = (n: { label: string; icon: ReactNode; to: Screen; count?: number }) => (
      <button
        key={n.label}
        onClick={() => go(n.to)}
        title={n.label}
        className={`flex w-full items-center gap-4 rounded-md border-l-[3px] px-3 py-3 text-left text-[15px] font-medium transition ${navActive[n.label] ? "border-primary bg-primary/15 text-accent" : "border-transparent text-ink hover:bg-line/50"}`}
      >
        <span className="text-accent">{n.icon}</span>
        <span className={`flex-1 ${labelCls}`}>{n.label}</span>
        {n.count && <span className={`text-sm text-muted ${labelCls}`}>{n.count}</span>}
      </button>
    );
    return (
      <>
        <nav className="space-y-1 px-2">{top.map(row)}</nav>
        <div className="flex-1" />
        <div className="mx-2 space-y-1 border-t border-line pt-3">{bottom.map(row)}</div>
      </>
    );
  };

  const BrandRow = ({ labelCls }: { labelCls: string }) => (
    <div className="flex items-center gap-3 px-4 pb-5 pt-1">
      <Logo size={34} />
      <span className={`text-xl font-semibold tracking-tight ${labelCls}`}>Groupy</span>
    </div>
  );

  const mobileNav = [
    { label: "Groups", short: "Groups", icon: Ic.groups, to: "dashboard" as Screen },
    { label: "Shared files", short: "Files", icon: Ic.folder, to: "files" as Screen },
    { label: "Calendar", short: "Calendar", icon: Ic.calendar, to: "calendar" as Screen, center: true },
    { label: "Notifications", short: "Alerts", icon: Ic.bell, to: "notifs" as Screen, badge: unreadCount },
    { label: "Settings", short: "Settings", icon: Ic.settings, to: "settings" as Screen },
  ];

  const FilterList = () => (
    <>
      {filterNames.map((n) => (
        <label key={n} className="flex cursor-pointer items-center gap-2 py-1.5 text-sm">
          <input type="checkbox" className="accent-[var(--primary)]" checked={!hidden.includes(n)} onChange={() => setHidden((h) => (h.includes(n) ? h.filter((x) => x !== n) : [...h, n]))} />
          <span className="truncate">{n}</span>
        </label>
      ))}
    </>
  );

  // ---------- header ----------
  const backTo: Partial<Record<Screen, Screen>> = { todo: "dashboard", feedback: "dashboard", group: "dashboard", create: "dashboard", join: "dashboard", day: "calendar", task: "group", request: "group", add: addCtx.from };
  const backScreen = backTo[screen];
  const title: ReactNode =
    screen === "dashboard" ? (<><span className="md:hidden">Groupy</span><span className="hidden md:inline">Groups</span></>)
    : screen === "todo" ? "To-do"
    : screen === "group" ? (<><button onClick={() => go("dashboard")} className="hidden text-muted hover:underline md:inline">Groups&nbsp;/&nbsp;</button><span className="truncate">{g.name}</span></>)
    : screen === "calendar" ? (
      <span className="flex items-center gap-0.5">
        <IconBtn label="Previous month" onClick={() => shiftMonth(-1)} className="!h-8 !w-8">{Ic.left}</IconBtn>
        <span className="min-w-[8.5rem] text-center">{new Date(month.y, month.m, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" })}</span>
        <IconBtn label="Next month" onClick={() => shiftMonth(1)} className="!h-8 !w-8">{Ic.right}</IconBtn>
      </span>)
    : screen === "day" ? fmtDate(selDate)
    : screen === "task" ? "Task details"
    : screen === "request" ? "Request details"
    : screen === "add" ? (addCtx.group ? (addAdmin ? "New task" : "Request task") : "Add personal task")
    : screen === "create" ? "Create group" : screen === "join" ? "Join group"
    : screen === "files" ? "Shared files" : screen === "notifs" ? "Notifications" : screen === "feedback" ? "Send feedback" : "Settings";

  const header = (
    <header className="relative z-20 shrink-0 border-b border-line bg-bg">
      <div className="flex h-14 items-center gap-1 px-2">
        {backScreen ? (
          <IconBtn label={screen === "add" ? "Close" : "Back"} onClick={() => go(backScreen)}>{screen === "add" ? Ic.close : Ic.back}</IconBtn>
        ) : (
          <span className="ml-2 md:hidden"><Logo size={28} /></span>
        )}
        <h1 className="ml-1 flex min-w-0 flex-1 items-center truncate text-lg font-semibold tracking-tight md:ml-3">{title}</h1>
        {screen === "add" && (
          <button
            disabled={!form.title.trim()}
            onClick={() => {
              const grp = addCtx.group ?? PERSONAL;
              if (addCtx.group && !addAdmin) {
                setRequests((l) => [{ id: Date.now(), gid: addCtx.gid, by: "You", title: form.title.trim(), date: form.date, allDay: form.allDay, start: form.start, end: form.end, repeat: form.repeat, deadline: form.deadline, details: form.details.trim(), posted: "Just now" }, ...l]);
                go("group");
                flash("Request sent to the CR");
                return;
              }
              setEvents((e) => [...e, { id: Date.now(), date: form.date, title: form.title.trim(), group: grp, color: addCtx.group ? undefined : form.color }]);
              if (addCtx.group) setTasks((t) => [{ id: Date.now(), gid: addCtx.gid, title: form.title.trim(), date: form.date, allDay: form.allDay, start: form.start, end: form.end, repeat: form.repeat, deadline: form.deadline, details: form.details.trim(), posted: "Just now" }, ...t]);
              const d = new Date(form.date + "T00:00");
              setMonth({ y: d.getFullYear(), m: d.getMonth() });
              setSelDate(form.date);
              go(addCtx.from === "group" ? "group" : addCtx.from === "day" ? "day" : "calendar");
              flash("Task saved");
            }}
            className="mr-1 h-9 rounded-md bg-primary px-5 text-sm font-semibold text-on-primary transition enabled:hover:brightness-105 disabled:opacity-40"
          >
            Save
          </button>
        )}
        {searchable && <IconBtn label="Search" onClick={() => { setSearchOpen((s) => !s); setQuery(""); }}>{Ic.search}</IconBtn>}
        <div className="relative">
          <button aria-label="Profile" onClick={() => setPop(pop === "profile" ? null : "profile")} className="grid h-9 w-9 place-items-center overflow-hidden rounded-md bg-primary text-on-primary transition active:scale-95">
            {avatar ? <img src={avatar} alt="" className="h-full w-full object-cover" /> : Ic.user}
          </button>
          {pop === "profile" && (
            <div className="absolute right-0 top-11 z-40 w-64 overflow-hidden rounded-md border border-line bg-surface py-1 shadow-xl" style={{ animation: "pop .15s ease-out" }}>
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-md bg-primary text-on-primary">
                  {avatar ? <img src={avatar} alt="" className="h-full w-full object-cover" /> : Ic.user}
                </span>
                <span className="min-w-0 truncate text-sm text-muted">{email || "Signed in"}</span>
              </div>
              <div className="h-px bg-line" />
              <button onClick={() => { setPop(null); avatarInput.current?.click(); }} className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                <span className="text-accent">{Ic.camera}</span> Change profile picture
              </button>
              {avatar && (
                <button onClick={() => { setAvatar(null); LS.del("groupy.avatar"); setPop(null); }} className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                  <span className="text-accent">{Ic.close}</span> Remove picture
                </button>
              )}
              <div className="my-1 h-px bg-line" />
              <button onClick={logout} className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                <span className="text-accent">{Ic.logout}</span> Logout
              </button>
            </div>
          )}
        </div>
        <div className="relative">
          <IconBtn label="More options" onClick={() => setPop(pop === "menu" ? null : "menu")}>{Ic.dots}</IconBtn>
          {pop === "menu" && (
            <div className="absolute right-0 top-11 z-40 w-52 overflow-hidden rounded-md border border-line bg-surface py-1 shadow-xl" style={{ animation: "pop .15s ease-out" }} role="menu">
              <button onClick={refresh} role="menuitem" className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                <span className="text-accent">{Ic.refresh}</span> Refresh
              </button>
              <button onClick={() => go("feedback")} role="menuitem" className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                <span className="text-accent">{Ic.feedback}</span> Feedback
              </button>
              <button onClick={() => { setDark((d) => !d); setPop(null); }} role="menuitem" className="flex w-full items-center gap-3 px-4 py-3 text-left text-[15px] hover:bg-line/50">
                <span className="text-accent">{Ic.moon}</span> {dark ? "Light mode" : "Dark mode"}
              </button>
            </div>
          )}
        </div>
      </div>
      {searchable && searchOpen && (
        <div className="px-3 pb-3">
          <div className="flex items-center gap-2 rounded-md border border-line bg-surface px-3 focus-within:border-primary">
            <span className="text-muted">{Ic.search}</span>
            <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder={screen === "files" ? "Search file names" : "Search notifications"} className="h-10 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted" />
            {query && <button aria-label="Clear" onClick={() => setQuery("")} className="text-muted">{Ic.close}</button>}
          </div>
        </div>
      )}
    </header>
  );

  const dueSoon = (
    <section className={`${card} p-4`}>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Due soon</h2>
        <button onClick={() => go("todo")} className="text-sm font-medium text-accent hover:underline">View to-do list</button>
      </div>
      <div className="mt-3 grid grid-cols-5 divide-x divide-line text-center">
        {[["0", "Today"], ["0", "Tomorrow"], ["1", "This week"], ["2", "This month"], ["1", "Later"]].map(([n, l]) => (
          <div key={l} className="px-0.5">
            <div className="text-xl font-semibold">{n}</div>
            <div className="text-[11px] leading-tight text-muted">{l}</div>
          </div>
        ))}
      </div>
    </section>
  );

  const taskCard = (t: GTask) => (
    <button key={t.id} onClick={() => { setTaskId(t.id); go("task"); }} className={`${card} flex w-full items-center gap-3 p-4 text-left transition hover:border-primary`}>
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/15 text-accent">{Ic.clipboard}</span>
      <div className="min-w-0">
        <p className="font-medium leading-snug">{t.title}</p>
        <p className="text-sm text-muted">{t.deadline ? `Due ${shortDate(t.deadline)}` : `Posted ${t.posted}`}</p>
      </div>
    </button>
  );

  const monthTitle = new Date(month.y, month.m, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });

  const taskView = (task: GTask) => (
            <div className="mx-auto w-full max-w-xl pb-6">
              <h2 className="break-words px-5 py-6 text-3xl font-medium leading-tight">{task.title}</h2>
              <div className="border-t border-line">
                <div className="flex items-center gap-5 px-5 py-4">
                  <span className="text-muted">{Ic.clock}</span>
                  <span className="flex-1 text-[15px]">{task.allDay ? "All-day" : "Timed"}</span>
                </div>
                <div className="pb-4 pl-[68px] pr-5 text-[15px]">
                  <p>{fmtDate(task.date)}</p>
                  {!task.allDay && <p className="mt-1 text-muted">{task.start} – {task.end}</p>}
                </div>
                <div className="flex items-center gap-5 border-t border-line px-5 py-4">
                  <span className="text-muted">{Ic.refresh}</span>
                  <span className="text-[15px]">{task.repeat}</span>
                </div>
              </div>
              <div className="border-t border-line">
                <div className="flex items-center gap-5 px-5 py-4">
                  <span className="text-muted">{Ic.target}</span>
                  <div>
                    <p className="text-xs text-muted">Deadline</p>
                    <p className={`text-[15px] ${task.deadline ? "" : "text-muted"}`}>{task.deadline ? fmtDate(task.deadline) : "No deadline"}</p>
                  </div>
                </div>
              </div>
              <div className="border-t border-line">
                <div className="flex items-start gap-5 px-5 py-4">
                  <span className="pt-0.5 text-muted">{Ic.details}</span>
                  <p className={`flex-1 whitespace-pre-wrap break-words text-[15px] leading-relaxed ${task.details ? "" : "text-muted"}`}>{task.details || "No details"}</p>
                </div>
              </div>
            </div>
  );

  const safeTop = "pt-[env(safe-area-inset-top)] max-md:pt-[max(env(safe-area-inset-top),2.75rem)]";
  if (!authed) {
    return (
      <div className={`h-full bg-bg text-ink ${safeTop}`}>
        <AuthFlow onDone={() => setAuthed(true)} />
      </div>
    );
  }

  return (
    <div className={`flex h-full bg-bg text-ink ${safeTop}`}>
      <input ref={avatarInput} type="file" accept="image/*" className="hidden" onChange={(e) => { pickAvatar(e.target.files?.[0]); e.target.value = ""; }} />
      {/* Persistent rail / sidebar */}
      <aside className="hidden shrink-0 flex-col border-r border-line bg-surface py-4 md:flex md:w-[76px] lg:w-64">
        <BrandRow labelCls="hidden lg:inline" />
        <NavList labelCls="hidden lg:inline" />
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col">
        {header}
        {pop === "profile" && <div className="fixed inset-0 z-10 bg-black/20" onClick={() => setPop(null)} />}
        {pop === "menu" && <div className="fixed inset-0 z-10" onClick={() => setPop(null)} />}

        <div className="relative min-h-0 flex-1">
        <main className="noscroll absolute inset-0 overflow-y-auto">
          {screen === "dashboard" && (
            <div className="mx-auto w-full max-w-6xl space-y-4 px-4 pb-28 pt-4 md:px-6">
              <div className="gap-4 md:grid md:grid-cols-[1fr_auto] md:items-stretch">
                {dueSoon}
                <div className="hidden items-center gap-2 md:flex">
                  <button onClick={() => go("create")} className="flex h-11 items-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-on-primary hover:brightness-105">{Ic.plus} Create group</button>
                  <button onClick={() => go("join")} className="flex h-11 items-center gap-2 rounded-md border border-line bg-surface px-4 text-sm font-semibold text-accent hover:bg-line/40">{Ic.login} Join group</button>
                </div>
              </div>
              <p className="pt-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted">Your groups</p>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {groupList.map((x) => (
                  <button key={x.id} onClick={() => openGroup(x.id)} className={`relative block h-36 w-full overflow-hidden rounded-lg text-left text-on-banner transition active:scale-[.985] ${x.alt ? "bg-banner-2" : "bg-banner"}`}>
                    <Shapes />
                    {x.unread > 0 && <span className="absolute right-0 top-0 grid h-9 min-w-11 place-items-center rounded-bl-lg bg-primary px-3 text-base font-bold text-on-primary">{x.unread}</span>}
                    <span className="absolute bottom-4 left-5 right-24">
                      <span className="block text-xl font-semibold leading-tight">{x.name}</span>
                      <span className="mt-1 block truncate text-sm opacity-80">{x.sub}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {screen === "todo" && (
            <div className="mx-auto w-full max-w-2xl px-4 pb-10 pt-2">
              <div className="border-b border-line">
                <span className="inline-block border-b-[3px] border-primary px-1 pb-2.5 pt-2 text-[15px] font-semibold text-accent">Assigned</span>
              </div>
              {todoSections.map((s) => {
                const isOpen = open.includes(s.label);
                return (
                  <div key={s.label} className="border-b border-line">
                    <button onClick={() => setOpen((o) => (isOpen ? o.filter((x) => x !== s.label) : [...o, s.label]))} className="flex w-full items-center justify-between py-4 text-left" aria-expanded={isOpen}>
                      <span className="text-base font-medium">{s.label}</span>
                      <span className="flex items-center gap-2 text-muted">
                        <span className="text-sm">{s.items.length}</span>
                        <span className={`transition ${isOpen ? "rotate-180" : ""}`}>{Ic.chevron}</span>
                      </span>
                    </button>
                    {isOpen && (
                      <div className="pb-3">
                        {s.items.length === 0 && <p className="pb-2 text-sm text-muted">Nothing here.</p>}
                        {s.items.map((t) => (
                          <div key={t.title} className="flex items-start gap-3 py-2.5">
                            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/15 text-accent">{Ic.clipboard}</span>
                            <div className="min-w-0">
                              <div className="font-medium leading-snug">{t.title}</div>
                              <div className="text-sm text-muted">{t.subject}</div>
                              <div className="text-sm text-accent">{t.due}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {screen === "group" && (
            <div className="mx-auto w-full max-w-4xl px-4 pb-8 pt-4 md:px-6">
              <div className="relative flex min-h-32 flex-col justify-between gap-4 overflow-hidden rounded-lg bg-banner p-5 text-on-banner">
                <Shapes />
                {g.admin && (
                  <button onClick={() => setEditGroup({ name: g.name, sub: g.demo ? g.sub : g.sub === "No description" ? "" : g.sub })} aria-label="Edit group" className="absolute right-3 top-3 z-10 grid h-9 w-9 place-items-center rounded-md border border-white/30 bg-white/15 transition hover:bg-white/25 active:scale-95">{Ic.pencil}</button>
                )}
                <div className="relative flex flex-wrap items-center gap-x-3 gap-y-2 pr-10">
                  <h2 className="text-2xl font-semibold leading-tight">{g.name}</h2>
                  {g.admin && (
                    <button onClick={copyCode} aria-label={`Copy group code ${g.code}`} className="flex items-center gap-2 rounded-md border border-white/30 bg-white/15 px-2.5 py-1 text-xs transition hover:bg-white/25 active:scale-95">
                      <span className="opacity-80">Group code</span>
                      <span className="font-mono text-sm font-semibold tracking-[0.18em]">{g.code}</span>
                      {Ic.copy}
                    </button>
                  )}
                </div>
                <p className="relative text-sm opacity-80">{g.sub} · {g.members} {g.members === 1 ? "member" : "members"}</p>
              </div>

              <div className="mt-4 flex border-b border-line" role="tablist">
                {([["history", "History", Ic.chat], ["tasks", "Tasks", Ic.clipboard], ["people", "People", Ic.groups], ...(g.admin ? [["requests", "Requests", Ic.megaphone]] : [])] as [Tab, string, ReactNode][]).map(([k, label, icon]) => (
                  <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`-mb-px flex flex-1 items-center justify-center gap-1.5 border-b-[3px] px-1 pb-2.5 pt-2 text-sm font-semibold transition sm:flex-none sm:gap-2 sm:px-6 sm:text-[15px] ${tab === k ? "border-primary text-accent" : "border-transparent text-muted hover:text-ink"}`}>
                    <span className={g.admin ? "hidden sm:block" : ""}>{icon}</span>{label}
                    {k === "requests" && gReqs.length > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-accent px-1 text-[11px] font-bold text-surface">{gReqs.length}</span>}
                  </button>
                ))}
              </div>

              <div className="mt-4 space-y-3">
                {(tab === "history" || tab === "tasks") && (
                  <button onClick={() => openAdd(TODAY, g.name)} className="flex h-12 w-full items-center justify-center gap-2 rounded-md bg-primary font-semibold text-on-primary transition hover:brightness-105 active:scale-[.985] md:w-auto md:px-8">
                    {Ic.pencil} {g.admin ? "Add task" : "Request task"}
                  </button>
                )}

                {tab === "history" && (
                  <>
                    <p className="pt-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted">History</p>
                    {gTasks.length === 0 && !g.demo && (
                      <Empty icon={Ic.chat} title="No activity yet" text={g.admin ? "Posts, files and tasks you share will show up here. Share the group code so classmates can join." : "Posts and files shared in this group will show up here."} />
                    )}
                    {gTasks.slice(0, 1).map((t) => (
                      <button key={t.id} onClick={() => { setTaskId(t.id); go("task"); }} className={`${card} flex w-full gap-3 p-4 text-left transition hover:border-primary`}>
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/15 text-accent">{Ic.clipboard}</span>
                        <div>
                          <p className="font-medium leading-snug">{t.title}</p>
                          <p className="mt-0.5 text-sm text-muted">{t.posted}</p>
                        </div>
                      </button>
                    ))}
                    {g.demo && (
                      <article className={`${card} p-4`}>
                        <div className="flex items-center gap-3">
                          <span className="grid h-10 w-10 place-items-center rounded-md bg-accent font-semibold text-surface">U</span>
                          <div>
                            <p className="font-medium">Umar Aftab</p>
                            <p className="text-sm text-muted">Sep 28</p>
                          </div>
                        </div>
                        <p className="mt-3 text-[15px] leading-relaxed">Book: Computer Networking: A Top-Down Approach, 9th Edition</p>
                        <div className="mt-3 flex items-center gap-3 rounded-md border border-line bg-bg px-3 py-2.5">
                          <span className="text-accent">{Ic.file}</span>
                          <span className="truncate text-sm font-medium">computer-networking-a-top-down-approach.pdf</span>
                        </div>
                      </article>
                    )}
                    {gTasks.slice(1).map((t) => (
                      <button key={t.id} onClick={() => { setTaskId(t.id); go("task"); }} className={`${card} flex w-full gap-3 p-4 text-left transition hover:border-primary`}>
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/15 text-accent">{Ic.clipboard}</span>
                        <div>
                          <p className="font-medium leading-snug">{t.title}</p>
                          <p className="mt-0.5 text-sm text-muted">{t.posted}</p>
                        </div>
                      </button>
                    ))}
                  </>
                )}

                {tab === "tasks" && (
                  <>
                    <p className="pt-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted">Upcoming deadlines</p>
                    {gTasks.length > 0 ? gTasks.map(taskCard) : <Empty icon={Ic.clipboard} title="No tasks yet" text="Tasks you create for this group will be listed here with their deadlines." />}
                  </>
                )}

                {tab === "requests" && g.admin && (
                  <>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Pending approval</p>
                    {gReqs.length === 0 && <Empty icon={Ic.check} title="No pending requests" text="Task requests from members will appear here for you to approve or decline." />}
                    {gReqs.map((r) => (
                      <article key={r.id} className={card}>
                        <button onClick={() => { setReqId(r.id); go("request"); }} className="flex w-full gap-3 p-4 pb-3 text-left">
                          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary/15 text-accent">{Ic.clipboard}</span>
                          <div className="min-w-0">
                            <p className="font-medium leading-snug">{r.title}</p>
                            <p className="mt-0.5 text-sm text-muted">Requested by {r.by} · {r.posted}</p>
                          </div>
                        </button>
                        <div className="flex gap-2 px-4 pb-4">
                          <button onClick={() => decline(r)} className="h-10 flex-1 rounded-md border border-line text-sm font-semibold text-danger transition hover:bg-line/40 active:scale-[.98]">Decline</button>
                          <button onClick={() => approve(r)} className="h-10 flex-1 rounded-md bg-primary text-sm font-semibold text-on-primary transition hover:brightness-105 active:scale-[.98]">Approve</button>
                        </div>
                      </article>
                    ))}
                  </>
                )}

                {tab === "people" && (g.demo ? ["Umar Aftab (CR)", "Hira Siddiqui", "Bilal Ahmed", "Ayesha Khan", "Zain Malik"] : [g.admin ? "You (CR)" : "You"]).map((n) => (
                  <div key={n} className="flex items-center gap-3 border-b border-line py-3">
                    <span className="grid h-10 w-10 place-items-center rounded-md bg-primary/20 font-semibold text-accent">{n[0]}</span>
                    <span className="font-medium">{n}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {screen === "calendar" && (
            <div className="flex h-full min-h-[34rem] gap-4 p-2 lg:p-4">
              <aside className="hidden w-60 shrink-0 space-y-4 lg:block">
                <button onClick={() => openAdd()} className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-semibold text-on-primary hover:brightness-105">{Ic.plus} Add personal task</button>
                <div className={`${card} p-4`}>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Filter</p>
                    <ModeToggle />
                  </div>
                  {calView === "group" ? <FilterList /> : <p className="py-1.5 text-sm text-muted">Showing only your personal tasks.</p>}
                </div>
                <button onClick={() => setColorSheet(true)} className="flex h-11 w-full items-center justify-center gap-2 rounded-md border border-line bg-surface text-sm font-semibold text-accent hover:bg-line/40">{Ic.palette} Colour scheme</button>
              </aside>
              <div
                className="flex min-w-0 flex-1 flex-col"
                onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
                onTouchEnd={(e) => { const dx = e.changedTouches[0].clientX - touchX.current; if (Math.abs(dx) > 60) shiftMonth(dx < 0 ? 1 : -1); }}
              >
                <div className="flex flex-wrap items-center gap-2 pb-2 lg:hidden">
                  <button onClick={() => setColorSheet(true)} className="flex h-9 items-center gap-2 rounded-md border border-line bg-surface px-3 text-sm font-medium text-accent">{Ic.palette} Colour scheme</button>
                  {calView === "group" && (
                    <button onClick={() => setFilterSheet(true)} className="flex h-9 items-center gap-2 rounded-md border border-line bg-surface px-3 text-sm font-medium text-accent">
                      {Ic.filter} Filter{hidden.length > 0 && <span className="text-muted">· {filterNames.length - hidden.length}/{filterNames.length}</span>}
                    </button>
                  )}
                  <div className="ml-auto"><ModeToggle /></div>
                </div>
                <div className="grid grid-cols-7 gap-1 pb-1 text-center text-xs font-medium text-muted" aria-label={monthTitle}>
                  {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => <div key={d}>{d}</div>)}
                </div>
                <div className="grid flex-1 grid-cols-7 grid-rows-6 gap-1">
                  {cells.map((d) => {
                    const k = key(d);
                    const inMonth = d.getMonth() === month.m;
                    const evs = events.filter((e) => e.date === k && (calView === "personal" ? e.group === PERSONAL : e.group !== PERSONAL && !hidden.includes(e.group)));
                    return (
                      <button key={k} onClick={() => { setSelDate(k); go("day"); }} className={`flex min-h-0 flex-col items-stretch gap-0.5 overflow-hidden rounded border p-1 text-left transition hover:border-primary ${k === TODAY ? "border-primary bg-primary/10" : "border-line bg-surface"} ${inMonth ? "" : "opacity-50"}`}>
                        <span className={`mx-auto grid h-6 min-w-6 place-items-center rounded text-xs font-semibold ${k === TODAY ? "bg-primary text-on-primary" : ""}`}>{d.getDate()}</span>
                        {evs.slice(0, 2).map((e) => (
                          <span key={e.id} style={{ background: colorOf(e) }} className="truncate rounded-[3px] px-1 text-[10px] font-medium leading-[16px] text-white lg:text-xs">{e.title}</span>
                        ))}
                        {evs.length > 2 && <span className="px-1 text-[10px] text-muted">+{evs.length - 2}</span>}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {screen === "day" && (() => {
            const dayEvents = events.filter((e) => e.date === selDate);
            return (
              <div className="mx-auto w-full max-w-2xl space-y-3 px-4 pb-28 pt-4">
                {selDate === TODAY && <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Today</p>}
                {dayEvents.length === 0 && <Empty icon={Ic.calendar} title="No tasks on this day" text="Tap the + button to add a personal task for this date." />}
                {dayEvents.map((e) => (
                  <article key={e.id} style={{ borderLeftColor: colorOf(e) }} className={`${card} flex items-center gap-3 p-4`}>
                    <span style={{ background: colorOf(e) }} className="grid h-10 w-10 shrink-0 place-items-center rounded-md text-white">{e.group === PERSONAL ? Ic.user : Ic.clipboard}</span>
                    <div className="min-w-0">
                      <p className="font-medium leading-snug">{e.title}</p>
                      <p className="truncate text-sm text-muted">{e.group}</p>
                    </div>
                  </article>
                ))}
              </div>
            );
          })()}

          {screen === "task" && task && taskView(task)}

          {screen === "request" && req && (
            <>
              <p className="mx-auto max-w-xl px-5 pt-4 text-sm text-muted">Requested by <span className="font-medium text-ink">{req.by}</span> · {req.posted}</p>
              {taskView(req)}
              <div className="mx-auto flex max-w-xl gap-2 px-5 pb-10">
                <button onClick={() => decline(req)} className="h-12 flex-1 rounded-md border border-line font-semibold text-danger transition hover:bg-line/40 active:scale-[.98]">Decline</button>
                <button onClick={() => approve(req)} className="h-12 flex-1 rounded-md bg-primary font-semibold text-on-primary transition hover:brightness-105 active:scale-[.98]">Approve</button>
              </div>
            </>
          )}

          {screen === "create" && (
            <form onSubmit={(e) => { e.preventDefault(); if (cg.title.trim()) createGroup(); }} className="mx-auto w-full max-w-xl pb-10">
              <input autoFocus value={cg.title} onChange={(e) => setCg({ ...cg, title: e.target.value })} placeholder="Group title" aria-label="Group title" className="w-full bg-transparent px-5 py-6 text-3xl font-medium outline-none placeholder:text-muted" />
              <div className="border-t border-line">
                <div className="flex items-center gap-5 px-5 py-4">
                  <span className="text-muted">{Ic.details}</span>
                  <input value={cg.sub} onChange={(e) => setCg({ ...cg, sub: e.target.value })} placeholder="Subtitle (course, section, timings)" aria-label="Subtitle" className="h-10 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted" />
                </div>
              </div>
              <div className="border-t border-line px-5 pt-5">
                <p className="mb-4 text-sm text-muted">You will be the admin. A group code is generated so classmates can join.</p>
                <button type="submit" disabled={!cg.title.trim()} className="flex h-12 w-full items-center justify-center gap-2 rounded-md bg-primary font-semibold text-on-primary transition enabled:hover:brightness-105 disabled:opacity-40">
                  {Ic.squarePlus} Create group
                </button>
              </div>
            </form>
          )}

          {screen === "join" && (
            <form onSubmit={(e) => { e.preventDefault(); if (joinCode.trim()) joinGroup(); }} className="mx-auto w-full max-w-xl px-5 pb-10 pt-8">
              <h2 className="text-3xl font-medium">Join a group</h2>
              <p className="mt-2 text-[15px] text-muted">Ask your CR for the group code and enter it below.</p>
              <input autoFocus value={joinCode} onChange={(e) => { setJoinCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "")); setJoinErr(""); }} maxLength={10} placeholder="GROUP CODE" aria-label="Group code" autoCapitalize="characters" autoComplete="off" className="mt-6 h-14 w-full rounded-md border border-line bg-surface px-4 text-center font-mono text-2xl font-semibold uppercase tracking-[0.3em] outline-none placeholder:text-base placeholder:font-sans placeholder:tracking-normal placeholder:text-muted focus:border-primary" />
              <p className="mt-2 min-h-5 text-sm text-danger" role="alert">{joinErr}</p>
              <button type="submit" disabled={!joinCode.trim()} className="mt-2 flex h-12 w-full items-center justify-center gap-2 rounded-md bg-primary font-semibold text-on-primary transition enabled:hover:brightness-105 disabled:opacity-40">
                {Ic.login} Join group
              </button>
              <p className="mt-4 text-center text-xs text-muted">Demo codes: OS5E26, SE5E26</p>
            </form>
          )}

          {screen === "add" && (
            <div className="mx-auto w-full max-w-xl pb-10">
              <input autoFocus value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Add title" className="w-full bg-transparent px-5 py-6 text-3xl font-medium outline-none placeholder:text-muted" />
              <div className="border-t border-line">
                <div className="flex items-center gap-5 px-5 py-4">
                  <span className="text-muted">{Ic.clock}</span>
                  <span className="flex-1 text-[15px]">All-day</span>
                  <button role="switch" aria-checked={form.allDay} onClick={() => setForm({ ...form, allDay: !form.allDay })} className={`relative h-6 w-11 rounded transition ${form.allDay ? "bg-primary" : "bg-line"}`}>
                    <span className={`absolute top-0.5 h-5 w-5 rounded-sm bg-surface shadow transition-all ${form.allDay ? "left-[22px]" : "left-0.5"}`} />
                  </button>
                </div>
                <div className="pb-3 pl-[68px] pr-5">
                  <label className="block">
                    <span className="text-[15px]">{fmtDate(form.date)}</span>
                    <input type="date" value={form.date} onChange={(e) => e.target.value && setForm({ ...form, date: e.target.value })} className="mt-1 block h-10 w-full rounded-md border border-line bg-surface px-3 text-sm outline-none focus:border-primary" />
                  </label>
                  {!form.allDay && (
                    <div className="mt-2 flex gap-2">
                      <input type="time" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} className="h-10 flex-1 rounded-md border border-line bg-surface px-3 text-sm outline-none focus:border-primary" />
                      <input type="time" value={form.end} onChange={(e) => setForm({ ...form, end: e.target.value })} className="h-10 flex-1 rounded-md border border-line bg-surface px-3 text-sm outline-none focus:border-primary" />
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-5 px-5 py-3">
                  <span className="text-muted">{Ic.refresh}</span>
                  <select value={form.repeat} onChange={(e) => setForm({ ...form, repeat: e.target.value })} className="h-10 flex-1 rounded-md bg-transparent text-[15px] outline-none">
                    {["Does not repeat", "Every day", "Every week", "Every month"].map((o) => <option key={o} className="bg-surface">{o}</option>)}
                  </select>
                </div>
              </div>
              <div className="border-t border-line">
                <div className="flex items-center gap-5 px-5 py-3">
                  <span className="text-muted">{Ic.target}</span>
                  <label className="flex-1">
                    <span className={`block text-[15px] ${form.deadline ? "" : "text-muted"}`}>{form.deadline ? fmtDate(form.deadline) : "Add deadline"}</span>
                    <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} className="mt-1 block h-10 w-full rounded-md border border-line bg-surface px-3 text-sm outline-none focus:border-primary" />
                  </label>
                </div>
              </div>
              {!addCtx.group && (
                <div className="border-t border-line">
                  <div className="flex items-center gap-5 px-5 py-4">
                    <span className="text-muted">{Ic.palette}</span>
                    <Swatches value={form.color} onPick={(i) => setForm({ ...form, color: i })} />
                  </div>
                </div>
              )}
              <div className="border-t border-line">
                <div className="flex items-start gap-5 px-5 py-4">
                  <span className="pt-0.5 text-muted">{Ic.details}</span>
                  <textarea value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} rows={3} placeholder="Add details" className="flex-1 resize-none bg-transparent text-[15px] outline-none placeholder:text-muted" />
                </div>
              </div>
            </div>
          )}

          {screen === "files" && (
            <div className="mx-auto w-full max-w-3xl space-y-3 px-4 pb-10 pt-4">
              {files.filter((f) => f.name.toLowerCase().includes(q)).map((f) => (
                <button key={f.name} onClick={() => setFileSel(f)} className={`${card} flex w-full items-center gap-4 p-3 text-left transition hover:border-primary`}>
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-primary text-on-primary">{fileIcon(f.type)}</span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{f.name}</span>
                    <span className="block truncate text-sm text-muted">{f.group} • {f.date}</span>
                  </span>
                </button>
              ))}
              {!files.some((f) => f.name.toLowerCase().includes(q)) && <p className="py-10 text-center text-muted">No files match "{query}".</p>}
            </div>
          )}

          {screen === "notifs" && (
            <div className="mx-auto w-full max-w-3xl space-y-3 px-4 pb-10 pt-4">
              {notifs.filter((n) => (n.text + n.group).toLowerCase().includes(q)).map((n) => (
                <button key={n.id} onClick={() => setNotifs((l) => l.map((x) => (x.id === n.id ? { ...x, unread: false } : x)))} className={`flex w-full items-center gap-4 rounded-lg border border-line border-l-[3px] bg-surface p-3 text-left transition hover:border-primary ${n.unread ? "border-l-primary" : "border-l-transparent"}`}>
                  <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-md ${n.unread ? "bg-primary text-on-primary" : "bg-primary/15 text-accent"}`}>{notifIcon(n.kind)}</span>
                  <span className="min-w-0">
                    <span className={`block leading-snug ${n.unread ? "font-bold" : "font-normal"}`}>{n.text}</span>
                    <span className="block truncate text-sm text-muted">{n.group} • {n.time}</span>
                  </span>
                </button>
              ))}
              <p className="pt-2 text-center text-xs text-muted">{unreadCount} unread</p>
            </div>
          )}

          {screen === "feedback" && (
            <div className="mx-auto w-full max-w-xl px-4 pb-10 pt-6">
              {fbSent ? (
                <div className={`${card} p-6 text-center`}>
                  <span className="mx-auto grid h-12 w-12 place-items-center rounded-md bg-primary text-on-primary">{Ic.check}</span>
                  <h2 className="mt-3 text-lg font-semibold">Thanks for the feedback</h2>
                  <p className="mt-1 text-sm text-muted">We read every message.</p>
                  <button onClick={() => { setFbSent(false); setFbText(""); setFbFile(""); }} className="mt-4 h-9 rounded-md border border-line px-4 text-sm font-medium text-accent hover:bg-line/40">Send another</button>
                </div>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); if (fbText.trim()) setFbSent(true); }} className="space-y-4">
                  <label className="block">
                    <span className="mb-1.5 block text-sm font-medium">Your feedback</span>
                    <textarea value={fbText} onChange={(e) => setFbText(e.target.value)} rows={7} placeholder="Describe your issue or suggestion" className="w-full resize-none rounded-md border border-line bg-surface p-3 text-[15px] outline-none placeholder:text-muted focus:border-primary" />
                  </label>
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="flex h-9 cursor-pointer items-center gap-2 rounded-md border border-line px-3 text-sm font-medium text-accent hover:bg-line/40">
                      {Ic.clip} Attach file
                      <input type="file" className="hidden" onChange={(e) => setFbFile(e.target.files?.[0]?.name ?? "")} />
                    </label>
                    {fbFile && <span className="truncate text-sm text-muted">{fbFile}</span>}
                  </div>
                  <button type="submit" disabled={!fbText.trim()} className="h-9 rounded-md bg-primary px-4 text-sm font-semibold text-on-primary transition enabled:hover:brightness-105 disabled:opacity-40">Submit feedback</button>
                </form>
              )}
            </div>
          )}

          {screen === "settings" && (
            <div className="mx-auto w-full max-w-xl px-4 pt-6">
              <div className={`${card} flex items-center gap-4 p-4`}>
                <span className="text-accent">{Ic.moon}</span>
                <span className="flex-1 font-medium">Dark mode</span>
                <button role="switch" aria-checked={dark} onClick={() => setDark(!dark)} className={`relative h-6 w-11 rounded transition ${dark ? "bg-primary" : "bg-line"}`}>
                  <span className={`absolute top-0.5 h-5 w-5 rounded-sm bg-surface shadow transition-all ${dark ? "left-[22px]" : "left-0.5"}`} />
                </button>
              </div>
            </div>
          )}
        </main>

        {screen === "dashboard" && (
          <button aria-label="Add group" onClick={() => setSheet(true)} className="absolute bottom-6 right-5 z-10 grid h-16 w-16 place-items-center rounded-lg bg-primary text-on-primary shadow-lg transition hover:brightness-105 active:scale-95 md:hidden">{Ic.plus}</button>
        )}
        {screen === "calendar" && (
          <button aria-label="Add personal task" onClick={() => openAdd()} className="absolute bottom-6 right-5 z-10 grid h-14 w-14 place-items-center rounded-md bg-accent text-bg shadow-lg transition hover:brightness-105 active:scale-95 lg:hidden">{Ic.plus}</button>
        )}
        {screen === "day" && (
          <button aria-label="Add personal task" onClick={() => openAdd(selDate)} className="absolute bottom-6 right-5 z-10 grid h-14 w-14 place-items-center rounded-md bg-accent text-bg shadow-lg transition hover:brightness-105 active:scale-95">{Ic.plus}</button>
        )}
        </div>

        {!hideNav && (
          <nav className="relative z-20 flex shrink-0 items-end justify-around border-t border-line bg-surface px-1 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1.5 md:hidden" aria-label="Primary">
            {mobileNav.map((n) => {
              const on = navActive[n.label];
              return n.center ? (
                <button key={n.label} aria-label={n.label} aria-current={on ? "page" : undefined} onClick={() => go(n.to)} className={`flex w-[4.5rem] flex-col items-center gap-0.5 text-[11px] font-medium ${on ? "text-accent" : "text-muted"}`}>
                  <span className={`-mt-6 grid h-14 w-14 place-items-center rounded-md border-4 border-bg shadow-md transition active:scale-95 [&>svg]:h-7 [&>svg]:w-7 ${on ? "bg-accent text-bg" : "bg-primary text-on-primary"}`}>{n.icon}</span>
                  {n.short}
                </button>
              ) : (
                <button key={n.label} aria-label={n.label} aria-current={on ? "page" : undefined} onClick={() => go(n.to)} className={`flex w-[4.5rem] flex-col items-center gap-0.5 py-1 text-[11px] font-medium ${on ? "text-accent" : "text-muted"}`}>
                  <span className={`relative grid h-7 w-12 place-items-center rounded-md transition ${on ? "bg-primary/20" : ""}`}>
                    {n.icon}
                    {!!n.badge && <span className="absolute right-1.5 top-0 h-2 w-2 rounded-full bg-accent" />}
                  </span>
                  {n.short}
                </button>
              );
            })}
          </nav>
        )}
      </div>

      {/* Create / join sheet */}
      {sheet && (
        <Modal onClose={() => setSheet(false)}>
          {([["Create group", Ic.squarePlus], ["Join group", Ic.login]] as const).map(([l, ic]) => (
            <button key={l} onClick={() => { setSheet(false); go(l === "Create group" ? "create" : "join"); }} className="flex w-full items-center gap-4 rounded-md px-4 py-4 text-left text-base font-medium hover:bg-line/50">
              <span className="text-accent">{ic}</span>
              {l}
            </button>
          ))}
        </Modal>
      )}

      {/* File detail */}
      {fileSel && (
        <Modal onClose={() => setFileSel(null)}>
          <div className="px-2 text-center">
            <span className="mx-auto grid h-16 w-16 place-items-center rounded-md bg-primary text-on-primary">{fileIcon(fileSel.type)}</span>
            <h2 className="mt-3 break-words text-lg font-semibold leading-snug">{fileSel.name}</h2>
            <dl className="mt-3 space-y-1 text-sm text-muted">
              <div>Uploaded by {fileSel.by}</div>
              <div>{fileSel.group} • {fileSel.date}</div>
              <div>{fileSel.size}</div>
            </dl>
            <button onClick={() => { setFileSel(null); flash("Download started"); }} className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary font-semibold text-on-primary hover:brightness-105">
              {Ic.download} {fileSel.type === "folder" ? "Open" : "Download"}
            </button>
          </div>
        </Modal>
      )}

      {colorSheet && (
        <Modal onClose={() => setColorSheet(false)}>
          <div className="max-h-[70vh] overflow-y-auto px-2">
            <h2 className="mb-3 text-lg font-semibold">Colour scheme</h2>
            <div className="space-y-4">
              {[...groupList.map((x) => x.name), PERSONAL].map((n, i) => (
                <div key={n}>
                  <p className="mb-2 truncate text-sm font-medium">{n === PERSONAL ? "Personal tasks (default)" : n}</p>
                  <Swatches value={groupColors[n] ?? (n === PERSONAL ? 1 : i)} onPick={(c) => setGroupColors((m) => ({ ...m, [n]: c }))} />
                </div>
              ))}
            </div>
          </div>
          <button onClick={() => setColorSheet(false)} className="mt-4 h-11 w-full rounded-md bg-primary font-semibold text-on-primary">Done</button>
        </Modal>
      )}

      {editGroup && (
        <Modal onClose={() => setEditGroup(null)}>
          <form onSubmit={(e) => {
            e.preventDefault();
            const name = editGroup.name.trim();
            if (!name) return;
            setGroupList((l) => l.map((x) => (x.id === g.id ? { ...x, name, sub: editGroup.sub.trim() || "No description" } : x)));
            setEditGroup(null);
            flash("Group updated");
          }} className="space-y-4 px-2">
            <h2 className="text-lg font-semibold">Edit group</h2>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">Title</span>
              <input autoFocus value={editGroup.name} onChange={(e) => setEditGroup({ ...editGroup, name: e.target.value })} className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">Subtitle</span>
              <input value={editGroup.sub} onChange={(e) => setEditGroup({ ...editGroup, sub: e.target.value })} className={inputCls} />
            </label>
            <div className="flex gap-2">
              <button type="button" onClick={() => setEditGroup(null)} className="h-11 flex-1 rounded-md border border-line font-semibold text-accent hover:bg-line/40">Cancel</button>
              <button type="submit" disabled={!editGroup.name.trim()} className="h-11 flex-1 rounded-md bg-primary font-semibold text-on-primary disabled:opacity-40">Save</button>
            </div>
          </form>
        </Modal>
      )}

      {filterSheet && (
        <Modal onClose={() => setFilterSheet(false)}>
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted">Filter</p>
          <div className="px-2"><FilterList /></div>
          <button onClick={() => setFilterSheet(false)} className="mt-4 h-11 w-full rounded-md bg-primary font-semibold text-on-primary">Done</button>
        </Modal>
      )}

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-[60] -translate-x-1/2 rounded-md bg-ink px-4 py-2 text-sm text-bg" style={{ animation: "pop .15s" }}>{toast}</div>
      )}
    </div>
  );
}
