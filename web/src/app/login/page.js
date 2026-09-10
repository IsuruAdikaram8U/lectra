'use client';
// Client Component: this page needs browser-only features — useState,
// useEffect, window.google (Google's script), and fetch() calls made
// directly from the visitor's own browser to the Django backend.

import { useEffect, useState } from 'react';
import Image from 'next/image';
import Script from 'next/script';

// Public identifier for your app — safe to embed in frontend code (unlike
// the Client Secret, which must stay backend-only). See backend/.env for
// the full explanation of why these two are treated so differently.
const GOOGLE_CLIENT_ID = '747170850766-voq3rt759r8lposqs40shh54uovbj8ri.apps.googleusercontent.com';

// Where Django is running locally. In a real deployment this would come
// from an environment variable instead of being hardcoded — fine for now
// since we're only running this against localhost.
const API_BASE_URL = 'http://127.0.0.1:8000';

export default function LoginPage() {
  // Which "mode" the card is showing right now. Rather than three separate
  // page routes, this one page just swaps what it renders based on this —
  // simpler for a flow where register naturally leads into "check your OTP".
  const [mode, setMode] = useState('login'); // 'login' | 'register' | 'verify-otp'

  // Every form field the card might need, across all three modes. Kept as
  // one object instead of one useState per field, since typing here is
  // straightforward and it keeps the component shorter.
  const [form, setForm] = useState({
    uomEmail: '',
    username: '',
    password: '',
    otpCode: '',
  });

  // A single helper that updates one field in `form` at a time, used by
  // every input's onChange below — avoids writing a separate handler
  // function for each individual field.
  const updateField = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  // UI feedback state: is a request currently in flight (disables the
  // button + shows a spinner-ish label), and the last error/success
  // message to show the user, if any.
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Google-specific state. idToken is kept around after a Google sign-in
  // attempt so the "link account" form can reuse it without asking the
  // user to click the Google button a second time.
  const [idToken, setIdToken] = useState(null);
  const [needsLinking, setNeedsLinking] = useState(false);
  const [linkPassword, setLinkPassword] = useState('');

  // Called after any successful login (password OR Google) — stores the
  // JWT pair and shows a success message. localStorage is the simplest
  // place to keep tokens for now; a production app would more likely use
  // httpOnly cookies (safer against XSS, since JS on the page can't read
  // them) — noted here as a deliberate simplification, not an oversight.
  const handleAuthSuccess = (data) => {
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    setSuccess('Logged in successfully!');
    setError('');
  };

  // ---- Password login (POST /api/token/) ----
  const handleLogin = async (e) => {
    e.preventDefault(); // stop the browser's default full-page form submit
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uom_email: form.uomEmail, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) {
        // SimpleJWT's error shape uses "detail" for bad credentials.
        setError(data.detail || 'Login failed.');
      } else {
        handleAuthSuccess(data);
      }
    } finally {
      setLoading(false);
    }
  };

  // ---- Registration (POST /api/auth/register/) ----
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uom_email: form.uomEmail,
          username: form.username,
          password: form.password,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        // DRF validation errors come back as an object keyed by field name
        // (e.g. {"uom_email": ["Only @uom.lk..."]})  — grab the first
        // message we can find, whatever field it's attached to.
        const firstError = Object.values(data)[0];
        setError(Array.isArray(firstError) ? firstError[0] : data.message || 'Registration failed.');
      } else {
        // Success — move to the OTP step rather than logging in yet.
        setMode('verify-otp');
        setSuccess(data.message);
      }
    } finally {
      setLoading(false);
    }
  };

  // ---- OTP verification (POST /api/auth/verify-otp/) ----
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/verify-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uom_email: form.uomEmail, otp_code: form.otpCode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Verification failed.');
      } else {
        handleAuthSuccess(data);
      }
    } finally {
      setLoading(false);
    }
  };

  // ---- Google Sign-In ----
  useEffect(() => {
    // Google's script calls this automatically the instant someone
    // successfully signs in via the button rendered below.
    // response.credential is the id_token — a signed JWT proving who they
    // are on Google's side.
    window.handleGoogleSignIn = async (response) => {
      setIdToken(response.credential);
      setError('');
      const res = await fetch(`${API_BASE_URL}/api/auth/google/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const data = await res.json();
      if (res.status === 404 && data.error === 'ACCOUNT_NOT_LINKED') {
        // Known Google account, but not tied to a uom_email account yet —
        // show the "prove your university identity" form instead of an error.
        setNeedsLinking(true);
      } else if (!res.ok) {
        setError(data.error || 'Google sign-in failed.');
      } else {
        handleAuthSuccess(data);
      }
    };
  }, []);

  // ---- Linking a Google account to an existing uom_email account ----
  const handleLinkSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/google/link/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken, uom_email: form.uomEmail, password: linkPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Linking failed.');
      } else {
        setNeedsLinking(false);
        handleAuthSuccess(data);
      }
    } finally {
      setLoading(false);
    }
  };

  // Small helper so the tab buttons and form-switching logic don't have to
  // repeat "clear error/success and reset relevant fields" everywhere.
  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
    setSuccess('');
  };

  return (
    // Full-height gradient backdrop, centering a single white card — the
    // standard modern auth-page layout.
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-blue-50 px-4">
      {/* Loads Google's Identity Services library once the page is
          interactive. onLoad is where we're guaranteed window.google
          actually exists, so that's where initialize/renderButton go. */}
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => {
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: window.handleGoogleSignIn,
          });
          window.google.accounts.id.renderButton(
            document.getElementById('google-signin-button'),
            { theme: 'outline', size: 'large', width: 320 }
          );
        }}
      />

      <div className="w-full max-w-md">
        {/* Brand header, sits above the card rather than inside it — a
            common pattern that keeps the card itself focused on the form. */}
                <div className="text-center mb-8">
          <Image
            src="/logo.png"
            alt="Lectra logo"
            width={64}
            height={64}
            className="mx-auto mb-3"
          />
          <h1 className="text-3xl font-bold text-slate-800">Lectra</h1>
          <p className="text-slate-500 mt-1">Smart Academic Timetable Management</p>
        </div>


        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8">
          {/* Only show the Login/Register tabs before OTP verification
              starts — once you're mid-registration, switching tabs away
              doesn't make sense. */}
          {mode !== 'verify-otp' && (
            <div className="flex bg-slate-100 rounded-lg p-1 mb-6">
              <button
                type="button"
                onClick={() => switchMode('login')}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'login' ? 'bg-white shadow text-indigo-600' : 'text-slate-500'
                }`}
              >
                Log In
              </button>
              <button
                type="button"
                onClick={() => switchMode('register')}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'register' ? 'bg-white shadow text-indigo-600' : 'text-slate-500'
                }`}
              >
                Register
              </button>
            </div>
          )}

          {/* Error / success banners — shared across every mode, so a
              message survives a mode switch until the next action clears it. */}
          {error && (
            <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          {success && !error && (
            <div className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
              {success}
            </div>
          )}

          {/* ---- LOGIN FORM ---- */}
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">University Email</label>
                <input
                  type="email"
                  required
                  placeholder="you@uom.lk"
                  value={form.uomEmail}
                  onChange={updateField('uomEmail')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={form.password}
                  onChange={updateField('password')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
              >
                {loading ? 'Logging in...' : 'Log In'}
              </button>
            </form>
          )}

          {/* ---- REGISTER FORM ---- */}
          {mode === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">University Email</label>
                <input
                  type="email"
                  required
                  placeholder="you@uom.lk"
                  value={form.uomEmail}
                  onChange={updateField('uomEmail')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
                <input
                  type="text"
                  required
                  placeholder="your_username"
                  value={form.username}
                  onChange={updateField('username')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={form.password}
                  onChange={updateField('password')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
              >
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          )}

          {/* ---- OTP VERIFICATION ---- */}
          {mode === 'verify-otp' && (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <p className="text-sm text-slate-500">
                We sent a 6-digit code to <span className="font-medium text-slate-700">{form.uomEmail}</span>.
                {' '}(Check the Django server console — local dev doesn&apos;t send real emails.)
              </p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Verification Code</label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  placeholder="123456"
                  value={form.otpCode}
                  onChange={updateField('otpCode')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-center text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
              >
                {loading ? 'Verifying...' : 'Verify & Continue'}
              </button>
            </form>
          )}

          {/* Google sign-in only makes sense on the login/register tabs,
              not mid-OTP-verification. */}
          {mode !== 'verify-otp' && (
            <>
              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 h-px bg-slate-200" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">or</span>
                <div className="flex-1 h-px bg-slate-200" />
              </div>

              {/* Google's script finds this empty div by id and injects
                  its own styled button into it. */}
              <div id="google-signin-button" className="flex justify-center"></div>
            </>
          )}

          {/* ---- Google account linking (only shown when needed) ---- */}
          {needsLinking && (
            <form onSubmit={handleLinkSubmit} className="mt-6 pt-6 border-t border-slate-100 space-y-4">
              <p className="text-sm text-slate-600">
                This Google account isn&apos;t linked to a Lectra profile yet.
                Enter your university credentials to link it:
              </p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">University Email</label>
                <input
                  type="email"
                  required
                  placeholder="you@uom.lk"
                  value={form.uomEmail}
                  onChange={updateField('uomEmail')}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={linkPassword}
                  onChange={(e) => setLinkPassword(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
              >
                {loading ? 'Linking...' : 'Link Google Account'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
