import { useEffect, useState } from "react";
import { Download, X, Share } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

/**
 * "Install App" button.
 *
 * Lets users install the Spam Detection System as a standalone app that runs
 * on their machine (PWA). When the browser fires `beforeinstallprompt` we use
 * the native install flow; otherwise (e.g. iOS Safari, or already dismissed)
 * we show short manual instructions.
 */
function isStandalone() {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    // iOS Safari
    window.navigator.standalone === true
  );
}

export default function InstallAppButton() {
  const { isDark } = useTheme();
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [installed, setInstalled] = useState(isStandalone());
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const onBeforeInstall = (e) => {
      e.preventDefault(); // stop the mini-infobar so we can trigger it from our button
      setDeferredPrompt(e);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  // Already running as an installed app — nothing to offer.
  if (installed) return null;

  const handleClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === "accepted") {
        setDeferredPrompt(null);
      }
    } else {
      // No native prompt available — show manual steps.
      setShowHelp(true);
    }
  };

  return (
    <>
      <button
        onClick={handleClick}
        title="Install this app on your device"
        className={`px-4 py-2.5 rounded-xl font-bold transition-all active:scale-95 flex items-center gap-2 shadow-md ${
          isDark
            ? "bg-slate-800 text-white hover:bg-slate-700"
            : "bg-white/35 text-slate-850 hover:bg-white/50"
        }`}
      >
        <Download size={18} />
        Install App
      </button>

      {showHelp && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div
            className={`w-full max-w-md rounded-3xl p-6 shadow-2xl border transition-all duration-300 ${
              isDark
                ? "bg-slate-900 text-slate-100 border-slate-700"
                : "bg-white text-slate-900 border-slate-200"
            }`}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <Download size={20} /> Install the app
              </h3>
              <button
                onClick={() => setShowHelp(false)}
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                  isDark
                    ? "bg-slate-800 hover:bg-slate-700"
                    : "bg-slate-100 hover:bg-slate-200"
                }`}
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-sm mb-4 opacity-80">
              Install Spam Detection System to run it as a standalone app on your
              machine — no browser tabs, works offline.
            </p>

            <div className="space-y-3 text-sm">
              <div>
                <p className="font-semibold mb-1">Chrome / Edge (desktop)</p>
                <p className="opacity-80">
                  Click the install icon in the address bar, or open the
                  browser menu → <em>Install Spam Detection System…</em>
                </p>
              </div>
              <div>
                <p className="font-semibold mb-1 flex items-center gap-1">
                  iPhone / iPad (Safari)
                </p>
                <p className="opacity-80 flex items-center gap-1 flex-wrap">
                  Tap <Share size={14} className="inline" /> Share →
                  <em>Add to Home Screen</em>.
                </p>
              </div>
              <div>
                <p className="font-semibold mb-1">Android (Chrome)</p>
                <p className="opacity-80">
                  Open the menu (⋮) → <em>Add to Home screen / Install app</em>.
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowHelp(false)}
              className="w-full mt-6 py-3 rounded-xl font-bold text-white shadow-md transition-all active:scale-95 bg-indigo-600 hover:bg-indigo-500"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}
