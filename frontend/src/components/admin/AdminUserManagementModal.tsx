import React, { useState, useEffect } from "react";
import { User, UserCreate, UserRole } from "../../types";
import { api } from "../../api/client";
import {
  X,
  UserPlus,
  KeyRound,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";



interface AdminUserManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AdminUserManagementModal: React.FC<AdminUserManagementModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New user form state
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newRole, setNewRole] = useState<UserRole>("DISTRICT_AUTHORITY");
  const [newDistrict, setNewDistrict] = useState("District-05");
  const [newState, setNewState] = useState("Maharashtra");
  const [newPassword, setNewPassword] = useState("");

  const loadUsers = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to load user accounts.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadUsers();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    const payload: UserCreate = {
      username: newUsername.trim(),
      email: newEmail.trim(),
      full_name: newFullName.trim(),
      role: newRole,
      assigned_district: newRole === "DISTRICT_AUTHORITY" ? newDistrict.trim() : null,
      assigned_state: newRole === "DISTRICT_AUTHORITY" ? newState.trim() : null,
      password: newPassword,
      is_active: true,
    };

    try {
      await api.createUser(payload);
      setSuccessMsg(`User '${newUsername}' created successfully.`);
      setShowAddForm(false);
      setNewUsername("");
      setNewEmail("");
      setNewFullName("");
      setNewPassword("");
      loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to create user.");
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      await api.updateUser(user.user_id, { is_active: !user.is_active });
      loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to update user status.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div
        className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">
                Statutory Access & RBAC User Management
              </h2>
              <p className="text-xs text-slate-400">
                MoSPI Officer, District Authority Territorial Scopes & Access Management
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Bar */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs font-semibold text-slate-600">
            Registered Platform Accounts: <strong>{users.length}</strong>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>{showAddForm ? "Cancel" : "Create Officer Account"}</span>
            </button>
            <button
              onClick={loadUsers}
              disabled={isLoading}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 transition-colors cursor-pointer"
              title="Refresh User List"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-4">
          {errorMsg && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Add User Form Drawer */}
          {showAddForm && (
            <form onSubmit={handleCreateUser} className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
              <div className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                Create New Statutory User
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Username</label>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. district_officer_05"
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                    required
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Full Officer Name</label>
                  <input
                    type="text"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    placeholder="e.g. Shri Ajay Kumar, IAS"
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                    required
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Email</label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="officer@nic.in"
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                    required
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as any)}
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                  >
                    <option value="MOSPI_OFFICER">MOSPI_OFFICER (National Scope)</option>
                    <option value="DISTRICT_AUTHORITY">DISTRICT_AUTHORITY (District Scope)</option>
                    <option value="ADMIN">ADMIN (System Administrator)</option>
                  </select>
                </div>
                {newRole === "DISTRICT_AUTHORITY" && (
                  <>
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Assigned District</label>
                      <input
                        type="text"
                        value={newDistrict}
                        onChange={(e) => setNewDistrict(e.target.value)}
                        placeholder="e.g. District-05"
                        className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                        required
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">Assigned State</label>
                      <input
                        type="text"
                        value={newState}
                        onChange={(e) => setNewState(e.target.value)}
                        placeholder="e.g. Maharashtra"
                        className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                        required
                      />
                    </div>
                  </>
                )}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter secure password"
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                    required
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700"
                >
                  Create User
                </button>
              </div>
            </form>
          )}

          {/* User Table */}
          <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Officer / User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Territorial Scope</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
                {users.map((u) => (
                  <tr key={u.user_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">{u.full_name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {u.username} • {u.email}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {u.role === "MOSPI_OFFICER" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                          MoSPI Officer
                        </span>
                      )}
                      {u.role === "DISTRICT_AUTHORITY" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          District Authority
                        </span>
                      )}
                      {u.role === "ADMIN" && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                          Administrator
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {u.role === "DISTRICT_AUTHORITY" ? (
                        <span className="font-semibold text-slate-700">
                          {u.assigned_district}, {u.assigned_state}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">National Scope (All India)</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-400">
                          <XCircle className="w-3.5 h-3.5 text-slate-400" /> Deactivated
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={`px-2.5 py-1 rounded text-[11px] font-bold border transition-colors cursor-pointer ${
                          u.is_active
                            ? "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                        }`}
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
