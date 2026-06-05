function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function setChatStatus(status, busy = false) {
  setText("chat-status", status);
  document.querySelector(".hero")?.classList.toggle("is-thinking", busy);
}

const API_BASE = "https://api.drinknile.com/api";

function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

function selectedAuthority() {
  const mode = document.querySelector('input[name="booking_authority"]:checked')?.value || "ask";
  const cap = Math.max(0, Math.min(5000, Number(document.getElementById("authority-cap")?.value || 75)));
  return { mode, cap };
}

function storeLocalIntent(intent) {
  const authority = selectedAuthority();
  const payload = {
    intent,
    booking_authority: authority.mode,
    cap: authority.cap,
    captured_at: new Date().toISOString(),
    source: window.location.hostname || "local-preview",
  };
  const local = JSON.parse(localStorage.getItem("evarian_intents") || "[]");
  local.push(payload);
  localStorage.setItem("evarian_intents", JSON.stringify(local.slice(-25)));
}

async function submitTripIntent(intent) {
  const authority = selectedAuthority();
  storeLocalIntent(intent);
  try {
    const response = await fetch(apiUrl("/trip-orders"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intent,
        wallet_cap: authority.cap,
        risk_mode: "balanced",
      }),
    });
    if (!response.ok) return { saved: false, authority };
    const order = await response.json();
    const permissions = {
      autonomy_level: authority.mode === "autopilot" ? 4 : 3,
      airport_ride_cap: authority.cap,
      auto_book_airport_rides: authority.mode === "autopilot",
      use_card_backup_under_cap: authority.mode === "autopilot",
    };
    await fetch(apiUrl(`/trip-orders/${order.id}/permissions`), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(permissions),
    });
    return { saved: true, authority };
  } catch {
    return { saved: false, authority };
  }
}

async function runHeroAgent(intent) {
  setChatStatus("Request received. Preparing the first trip brief...", true);
  const { saved, authority } = await submitTripIntent(intent);
  setChatStatus(
    saved && authority.mode === "autopilot"
      ? `Captured. Scoped autopilot is set for airport rides up to $${authority.cap}.`
      : saved
      ? "Captured. Evarian will ask before charges or booking."
      : "Captured locally. The live booking agent is still coming online.",
    false,
  );
}

async function submitWaitlist(email) {
  const payload = {
    email,
    source: window.location.hostname || "local-preview",
    product: "evarian-travel-os",
    joined_at: new Date().toISOString(),
  };
  const local = JSON.parse(localStorage.getItem("evarian_waitlist") || "[]");
  local.push(payload);
  localStorage.setItem("evarian_waitlist", JSON.stringify(local.slice(-50)));

  try {
    const response = await fetch(apiUrl("/waitlist"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.ok ? "server" : "local";
  } catch {
    return "local";
  }
}

document.getElementById("hero-command-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("hero-intent");
  const intent = input.value.trim() || "Adventure awaits";
  runHeroAgent(intent);
});

document.querySelectorAll('input[name="booking_authority"]').forEach((input) => {
  input.addEventListener("change", () => {
    document.querySelectorAll(".authority-option").forEach((label) => {
      const radio = label.querySelector("input");
      label.classList.toggle("is-selected", radio?.checked);
    });
  });
});
document.querySelector('input[name="booking_authority"]:checked')?.dispatchEvent(new Event("change"));

document.getElementById("waitlist-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("waitlist-email").value.trim();
  const message = document.getElementById("waitlist-message");
  if (!email) return;
  message.textContent = "Adding you...";
  const destination = await submitWaitlist(email);
  message.textContent = destination === "server"
    ? "You are on the list. We will send early access as Evarian comes online."
    : "Saved in this browser. Use the live site to join the hosted list.";
  event.target.reset();
});

const heroVideo = document.querySelector(".hero-video");
const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)");
if (heroVideo && reduceMotion?.matches) {
  heroVideo.pause();
  heroVideo.removeAttribute("autoplay");
}
