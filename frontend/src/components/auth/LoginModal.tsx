import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  ShieldAlert,
  Lock,
  User as UserIcon,
  Landmark,
  ArrowRight,
  AlertCircle,
  Building2,
  ShieldCheck,
  KeyRound,
} from "lucide-react";


interface LoginModalProps {
  isOpen: boolean;
  onClose?: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const { login, loginError } = useAuth();
  const [username, setUsername] = useState("mospi_officer");
  const [password, setPassword] = useState("MoSPI@2026");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg("Please enter both username and password.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await login({ username: username.trim(), password: password.trim() });
      if (onClose) onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || "Authentication failed. Check credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoCredentials = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setErrorMsg(null);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div
        className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Government Banner */}
        <div className="bg-slate-900 px-6 py-3 text-white flex items-center justify-between text-xs border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Landmark className="w-4 h-4 text-blue-400" />
            <span className="font-medium tracking-wide">Government of India • MoSPI</span>
          </div>
          <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded text-blue-300 font-semibold">
            SIH 26102
          </span>
        </div>

        {/* Header Branding */}
        <div className="p-6 pb-4 text-center border-b border-slate-100 bg-slate-50/50">
          <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-white mx-auto shadow-sm mb-3">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            MPLADS-IntelliTrack
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Statutory AI Monitoring & Case Management Portal
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {(errorMsg || loginError) && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMsg || loginError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Username
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username..."
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/40 text-slate-800 font-medium"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password..."
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/40 text-slate-800 font-medium"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-sm cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <span>Sign In with Statutory Credentials</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          {/* Seeded Accounts Quick-Fill Panel for Evaluators */}
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-bold uppercase tracking-wider">Evaluation Demo Accounts:</span>
              <span className="text-[10px] text-slate-400">Click to load</span>
            </div>

            <div className="grid grid-cols-1 gap-1.5">
              <button
                type="button"
                onClick={() => setDemoCredentials("mospi_officer", "MoSPI@2026")}
                className="w-full p-2 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 text-left transition-all flex items-center justify-between cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600 group-hover:scale-105 transition-transform" />
                  <div>
                    <div className="text-xs font-bold text-slate-800">MoSPI Officer (National Scope)</div>
                    <div className="text-[10px] text-slate-500 font-mono">mospi_officer • All India</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                  Select
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDemoCredentials("district_officer_04", "District@2026")}
                className="w-full p-2 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 text-left transition-all flex items-center justify-between cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-emerald-600 group-hover:scale-105 transition-transform" />
                  <div>
                    <div className="text-xs font-bold text-slate-800">District Authority (District-04)</div>
                    <div className="text-[10px] text-slate-500 font-mono">district_officer_04 • District-04 Only</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                  Select
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDemoCredentials("admin_user", "Admin@2026")}
                className="w-full p-2 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 text-left transition-all flex items-center justify-between cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-amber-600 group-hover:scale-105 transition-transform" />
                  <div>
                    <div className="text-xs font-bold text-slate-800">System Administrator</div>
                    <div className="text-[10px] text-slate-500 font-mono">admin_user • User Management</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">
                  Select
                </span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
