import { useState } from "react";
import { apiGet, clearCredentials, setBasicCredentials } from "../api/client";

export default function SingleUserLogin({ onAuthenticated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setBasicCredentials(username, password);
      const identity = await apiGet("/auth/me");
      setPassword("");
      onAuthenticated(identity);
    } catch {
      clearCredentials();
      setError("Sign-in failed. Check the username and password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090d] px-5 text-white">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-xl border border-white/[0.08] bg-white/[0.025] p-7"
      >
        <h1 className="text-xl font-semibold">Learning Assistant</h1>
        <p className="mt-2 text-sm text-zinc-500">Sign in to continue.</p>

        <label className="mt-6 block text-xs font-medium text-zinc-400">
          Username
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-2 w-full rounded-lg border border-white/[0.1] bg-black/20 px-3 py-2.5 text-sm outline-none focus:border-violet-400/40"
          />
        </label>

        <label className="mt-4 block text-xs font-medium text-zinc-400">
          Password
          <input
            autoComplete="current-password"
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-lg border border-white/[0.1] bg-black/20 px-3 py-2.5 text-sm outline-none focus:border-violet-400/40"
          />
        </label>

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="mt-6 w-full rounded-lg bg-violet-500 px-4 py-2.5 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}