import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  Activity,
  FolderGit2,
  GitCommitHorizontal,
  LayoutDashboard,
  Network,
  Sparkles,
} from "lucide-react";
import type { Repository } from "../../api/types";

interface AppShellProps {
  repositories: Repository[];
  activeRepoId: number | null;
  onSelectRepo: (repoId: number) => void;
  aiEnabled: boolean;
  children: ReactNode;
}

export function AppShell({
  repositories,
  activeRepoId,
  onSelectRepo,
  aiEnabled,
  children,
}: AppShellProps) {
  const navItems = [
    { to: "/", label: "Repositories", icon: FolderGit2 },
    { to: "/overview", label: "Overview", icon: LayoutDashboard },
    { to: "/graph", label: "Dependency Graph", icon: Network },
    { to: "/analyze", label: "Change Analysis", icon: GitCommitHorizontal },
  ];

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex">
      <aside className="w-64 shrink-0 bg-surface-900 border-r border-slate-800/80 flex flex-col">
        <div className="p-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="font-semibold text-sm tracking-tight">ChangeScope AI</div>
              <div className="text-[11px] text-slate-400">Impact Analysis Platform</div>
            </div>
          </div>
        </div>

        <div className="p-3 border-b border-slate-800/80">
          <label className="block text-[11px] uppercase tracking-wider text-slate-400 mb-1.5 font-medium">
            Active Repository
          </label>
          <select
            value={activeRepoId ?? ""}
            onChange={(e) => {
              const val = Number(e.target.value);
              if (val) onSelectRepo(val);
            }}
            className="w-full bg-surface-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {repositories.length === 0 && <option value="">No repositories</option>}
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-800"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-800/80 text-xs flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1.5">
            <Sparkles className={`w-3.5 h-3.5 ${aiEnabled ? "text-emerald-400" : "text-slate-500"}`} />
            Claude Advisory
          </span>
          <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-800 border border-slate-700">
            {aiEnabled ? "READY" : "OFFLINE"}
          </span>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-6">{children}</div>
      </main>
    </div>
  );
}
