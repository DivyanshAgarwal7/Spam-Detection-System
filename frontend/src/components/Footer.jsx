import { useTheme } from "../context/ThemeContext";
import SpamLogo from "/src/assets/SpamLogo.png";

const FEATURES = [
  "Email Spam Detection",
  "SMS Spam Detection",
  "URL Security Analysis",
  "Real-Time Scanning",
];

export default function Footer() {
  const { isDark, activeTheme } = useTheme();

  return (
    <footer
      className={`w-full mt-4 p-6 sm:p-8 text-center transition-all duration-500 ${
    isDark ? activeTheme.cardDark : `${activeTheme.card} backdrop-blur-md`
  }`}
    >
      <div className="flex items-center justify-center gap-3 mb-3">
        <img src={SpamLogo} alt="Spam Logo" className="w-12 h-10 object-contain" />
        <span className="text-lg font-extrabold tracking-tight">
          Spam Detection System
        </span>
      </div>

      <p className="text-xs sm:text-sm font-semibold opacity-75 mb-5 leading-relaxed max-w-md mx-auto">
        Protecting users from Email Spam, SMS Fraud, Phishing URLs, and Online
        Threats through intelligent detection and cybersecurity awareness.
      </p>

      <div className="grid grid-cols-2 gap-2 text-[11px] sm:text-xs font-bold  max-w-xs mx-auto">
        {FEATURES.map((feature) => (
          <span
            key={feature}
            className={`px-3 py-2 rounded-xl border ${
              isDark
                ? "bg-slate-800/60 border-slate-700/60"
                : "bg-white/40 border-white/30"
            }`}
          >
            {feature}
          </span>
        ))}
      </div>

      <div className="mb-5">
        <h3 className="text-xs sm:text-sm font-extrabold uppercase tracking-wide opacity-60 mb-1">
          Our Mission
        </h3>
        <p className="text-xs sm:text-sm font-semibold opacity-75 leading-relaxed max-w-md mx-auto">
          To help users identify and avoid spam, phishing attempts, fraudulent
          messages, and malicious links through advanced security solutions
          and user awareness.
        </p>
      </div>

      <p
        className={`text-xs sm:text-sm font-extrabold mb-4 px-3 py-2 rounded-xl inline-block ${activeTheme.accent}`}
      >
        Stay Safe. Stay Alert. Verify Before You Click.
      </p>

      <p className="text-[11px] font-semibold opacity-60">
        © 2026 Spam Detection System. All Rights Reserved.
      </p>
    </footer>
  );
}
