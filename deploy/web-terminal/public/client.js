"use strict";

const statusEl = document.getElementById("status");
const reconnectButton = document.getElementById("reconnect");
const logoutButton = document.getElementById("logout");
const activeUserEl = document.getElementById("active-user");
const loginPanel = document.getElementById("login-panel");
const terminalPanel = document.getElementById("terminal-panel");
const terminalEl = document.getElementById("terminal");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");

let fitAddon = null;
let term = null;
let socket = null;
let resizeTimer = null;
let socketVersion = 0;

function socketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

function setStatus(text, state = "idle") {
  statusEl.textContent = text;
  statusEl.dataset.state = state;
}

function setUser(username, authenticated) {
  activeUserEl.textContent = username || "Guest";
  logoutButton.hidden = !authenticated;
}

function ensureTerminal() {
  if (term) {
    return;
  }

  fitAddon = new FitAddon.FitAddon();
  term = new Terminal({
    cursorBlink: true,
    fontFamily: '"Cascadia Mono", "JetBrains Mono", Consolas, "Courier New", monospace',
    fontSize: 15,
    lineHeight: 1.08,
    theme: {
      background: "#05070b",
      foreground: "#eaf7ff",
      cursor: "#f7d76b",
      black: "#10141b",
      blue: "#6bb7ff",
      cyan: "#3be3d0",
      green: "#93f071",
      magenta: "#ff78c8",
      red: "#ff5f76",
      white: "#f8fbff",
      yellow: "#f7d76b",
    },
  });

  term.loadAddon(fitAddon);
  term.open(terminalEl);
  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "input", data }));
    }
  });
}

function sendResize() {
  if (!term || !socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  socket.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
}

function fitTerminal() {
  if (!fitAddon) {
    return;
  }
  fitAddon.fit();
  sendResize();
}

function showLogin(message = "") {
  loginPanel.hidden = false;
  terminalPanel.hidden = true;
  reconnectButton.disabled = true;
  loginError.textContent = message;
  setStatus("Login richiesto per aprire il cabinato.", "warning");
  window.requestAnimationFrame(() => document.getElementById("username").focus());
}

function showArcade(username) {
  loginPanel.hidden = true;
  terminalPanel.hidden = false;
  reconnectButton.disabled = false;
  setUser(username, true);
  ensureTerminal();
  window.requestAnimationFrame(() => {
    fitTerminal();
    term.focus();
  });
}

async function loadSession() {
  const response = await fetch("/session", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("session unavailable");
  }
  return response.json();
}

async function checkSession() {
  if (window.location.protocol === "https:") {
    setStatus("Usa http:// su questa porta: il cabinato non espone TLS.", "error");
    return;
  }

  try {
    const session = await loadSession();
    if (!session.authenticated) {
      setUser("", false);
      showLogin();
      return;
    }

    showArcade(session.username);
    connect();
  } catch {
    setStatus("Servizio arcade non raggiungibile sulla VM.", "error");
  }
}

function connect() {
  if (!term) {
    return;
  }

  socketVersion += 1;
  const currentSocket = socketVersion;
  if (socket) {
    socket.close();
  }

  term.clear();
  setStatus("Connessione al cabinato...", "warning");
  socket = new WebSocket(socketUrl());

  socket.addEventListener("open", () => {
    if (currentSocket !== socketVersion) {
      return;
    }
    setStatus(`Connesso come ${activeUserEl.textContent}`, "ok");
    fitTerminal();
    term.focus();
  });

  socket.addEventListener("message", (event) => {
    if (currentSocket !== socketVersion) {
      return;
    }
    const message = JSON.parse(event.data);
    if (message.type === "output") {
      term.write(message.data);
    }
    if (message.type === "exit") {
      setStatus(`Sessione chiusa (${message.exitCode}). Premi Reconnect per rigiocare.`, "warning");
    }
  });

  socket.addEventListener("close", (event) => {
    if (currentSocket !== socketVersion) {
      return;
    }
    if (event.code === 1008 || event.code === 1006) {
      showLogin("Sessione scaduta o non autorizzata.");
      return;
    }
    setStatus("Disconnesso. Premi Reconnect per aprire una nuova partita.", "warning");
  });

  socket.addEventListener("error", () => {
    if (currentSocket !== socketVersion) {
      return;
    }
    setStatus("Errore di connessione. Controlla il servizio arcade sulla VM.", "error");
  });
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  const username = document.getElementById("username").value.trim();
  const accessCode = document.getElementById("access-code").value;

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, accessCode }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      loginError.textContent = payload.error || "Accesso non riuscito.";
      setStatus("Accesso rifiutato.", "error");
      return;
    }

    showArcade(payload.username);
    connect();
  } catch {
    loginError.textContent = "Servizio non raggiungibile.";
    setStatus("Servizio arcade non raggiungibile.", "error");
  }
});

logoutButton.addEventListener("click", async () => {
  socketVersion += 1;
  if (socket) {
    socket.close();
  }
  await fetch("/logout", { method: "POST" }).catch(() => {});
  setUser("", false);
  showLogin();
});

window.addEventListener("resize", () => {
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(fitTerminal, 80);
});

reconnectButton.addEventListener("click", connect);

checkSession();
