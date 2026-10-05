import { useEffect, useState } from "react";
import {
  BookOpen,
  Brain,
  FileText,
  Home,
  Layers3,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  Sparkles,
} from "lucide-react";

import HomePage from "./pages/Home";
import Ask from "./pages/Ask";
import Quiz from "./pages/Quiz";
import Flashcards from "./pages/Flashcards";
import Notes from "./pages/Notes";
import SingleUserLogin from "./components/SingleUserLogin";
import { apiGet, clearCredentials } from "./api/client";

const navigation = [
  { id: "home", label: "Home", icon: Home },
  { id: "ask", label: "Ask", icon: MessageSquare },
  { id: "quiz", label: "Quiz", icon: Brain },
  { id: "flashcards", label: "Flashcards", icon: Layers3 },
  { id: "notes", label: "Notes", icon: FileText },
];

function App() {
  const [activePage, setActivePage] = useState("home");
  const [collapsed, setCollapsed] = useState(false);
  const [auth, setAuth] = useState({ ready: false, required: false, identity: null, error: false });

  useEffect(() => {
    let active = true;

    async function checkAuth() {
      try {
        const { required } = await apiGet("/auth/status");
        if (!required) {
          if (active) setAuth({ ready: true, required: false, identity: null, error: false });
          return;
        }

        try {
          const identity = await apiGet("/auth/me");
          if (active) setAuth({ ready: true, required: true, identity, error: false });
        } catch {
          clearCredentials();
          if (active) setAuth({ ready: true, required: true, identity: null, error: false });
        }
      } catch {
        if (active) setAuth({ ready: true, required: false, identity: null, error: true });
      }
    }

    checkAuth();
    return () => {
      active = false;
    };
  }, []);

  if (!auth.ready) {
    return <div className="flex min-h-screen items-center justify-center bg-[#08090d] text-sm text-zinc-500">Connecting...</div>;
  }

  if (auth.error) {
    return <div className="flex min-h-screen items-center justify-center bg-[#08090d] text-sm text-zinc-400">Unable to connect to the API.</div>;
  }

  function signOut() {
    clearCredentials();
    setAuth({ ready: true, required: true, identity: null, error: false });
    setActivePage("ask");
  }

  const current = navigation.find((item) => item.id === activePage);

  function renderPage() {
    if (
      auth.required &&
      !auth.identity &&
      ["quiz", "flashcards"].includes(activePage)
    ) {
      return (
        <SingleUserLogin
          onAuthenticated={(identity) =>
            setAuth({ ready: true, required: true, identity, error: false })
          }
        />
      );
    }

    switch (activePage) {
      case "ask":
        return <Ask collapsed={collapsed} />;
      case "quiz":
        return <Quiz />;
      case "flashcards":
        return <Flashcards />;
      case "notes":
        return <Notes />;
      default:
        return <HomePage setActivePage={setActivePage} />;
    }
  }

  return (
    <div className="flex min-h-screen bg-[#08090d] text-white">
      <aside
        className={`fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-white/[0.07] bg-[#0b0c11]/95 backdrop-blur-xl transition-all duration-300 ${
          collapsed ? "w-[76px]" : "w-[250px]"
        }`}
      >
        <div className="flex h-20 items-center border-b border-white/[0.06] px-5">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 ring-1 ring-violet-400/20">
              <Sparkles className="h-5 w-5 text-violet-300" />
            </div>

            {!collapsed && (
              <div>
                <div className="whitespace-nowrap text-sm font-semibold">
                  Learning Assistant
                </div>
                <div className="text-xs text-zinc-500">
                  AI study workspace
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 px-3 py-5">
          {!collapsed && (
            <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
              Workspace
            </div>
          )}

          <nav className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = activePage === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                    active
                      ? "bg-violet-500/12 text-violet-200 ring-1 ring-violet-400/10"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-100"
                  }`}
                >
                  <Icon
                    className={`h-[18px] w-[18px] shrink-0 ${
                      active ? "text-violet-300" : "text-zinc-500"
                    }`}
                  />

                  {!collapsed && <span>{item.label}</span>}
                </button>
              );
            })}
          </nav>

          <div className="my-6 h-px bg-white/[0.06]" />

          {!collapsed && (
            <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
              Materials
            </div>
          )}

          <div className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-3">
            <div className="flex items-center gap-3">
              <BookOpen className="h-4 w-4 shrink-0 text-zinc-500" />

              {!collapsed && (
                <div>
                  <div className="text-xs text-zinc-300">
                    Study library
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-600">
                    2 documents indexed
                  </div>
                </div>
              )}
            </div>

            {!collapsed && (
              <button className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-white/[0.07] py-2 text-xs text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-300">
                <Plus className="h-3.5 w-3.5" />
                Add material
              </button>
            )}
          </div>
        </div>

        <div className="border-t border-white/[0.06] p-3">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-200"
          >
            {collapsed ? (
              <PanelLeftOpen className="h-[18px] w-[18px]" />
            ) : (
              <PanelLeftClose className="h-[18px] w-[18px]" />
            )}

            {!collapsed && (
              <span className="text-sm">Collapse sidebar</span>
            )}
          </button>

          <button className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-200">
            <Settings className="h-[18px] w-[18px]" />

            {!collapsed && <span className="text-sm">Settings</span>}
          </button>
        </div>
      </aside>

      <main
        className={`min-h-screen flex-1 transition-all duration-300 ${
          collapsed ? "ml-[76px]" : "ml-[250px]"
        }`}
      >
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-white/[0.06] bg-[#08090d]/80 px-8 backdrop-blur-xl">
          <div>
            <div className="text-sm font-medium text-zinc-300">
              {current?.label}
            </div>

            <div className="text-xs text-zinc-600">
              AI-powered study workspace
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activePage !== "ask" && (
              <button
                onClick={() => setActivePage("ask")}
                className="flex items-center gap-2 rounded-xl bg-violet-500 px-4 py-2.5 text-sm font-medium hover:bg-violet-400"
              >
                <MessageSquare className="h-4 w-4" />
                Ask
              </button>
            )}
            {auth.identity && (
              <button
                onClick={signOut}
                title="Sign out"
                className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/[0.08] text-zinc-400 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>

        <section className="mx-auto max-w-7xl px-8 py-10">
          {renderPage()}
        </section>
      </main>
    </div>
  );
}

export default App;