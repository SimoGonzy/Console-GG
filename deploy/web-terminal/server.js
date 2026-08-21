"use strict";

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");
const { WebSocket, WebSocketServer } = require("ws");
const pty = require("node-pty");

const host = process.env.CONSOLE_GG_HOST || "0.0.0.0";
const port = Number(process.env.CONSOLE_GG_PORT || 7681);
const appDir = process.env.CONSOLE_GG_APP_DIR || "C:\\ConsoleGG";
const defaultStateDir = process.env.CONSOLE_GG_APP_DIR
  ? path.join(appDir, ".console-gg-data")
  : "C:\\ProgramData\\ConsoleGG";
const stateDir = process.env.CONSOLE_GG_STATE_DIR || defaultStateDir;
const publicDir = path.join(__dirname, "public");
const runScript = path.join(appDir, "deploy", "windows", "run-console-gg.ps1");

const allowedUsers = parseAllowedUsers(process.env.CONSOLE_GG_ALLOWED_USERS || "");
const accessCode = process.env.CONSOLE_GG_ACCESS_CODE || "";
const sessionSecret =
  process.env.CONSOLE_GG_SESSION_SECRET || accessCode || "console-gg-local-session";
const sessionCookieName = "console_gg_session";
const sessionTtlSeconds = Number(process.env.CONSOLE_GG_SESSION_TTL_SECONDS || 43200);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

function parseAllowedUsers(raw) {
  return new Set(
    raw
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  );
}

function loginRequired() {
  return allowedUsers.size > 0 || accessCode.length > 0;
}

function sendJson(res, statusCode, payload, headers = {}) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers,
  });
  res.end(JSON.stringify(payload));
}

function sendFile(res, filePath) {
  if (!filePath) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not found");
    return;
  }

  fs.readFile(filePath, (error, data) => {
    if (error) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }

    res.writeHead(200, {
      "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    res.end(data);
  });
}

function safePublicPath(urlPath) {
  const safePath = path.normalize(urlPath.replace(/^\/+/, ""));
  const candidate = path.join(publicDir, safePath);
  const relative = path.relative(publicDir, candidate);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    return null;
  }
  return candidate;
}

function resolveAssetPath(urlPath) {
  if (urlPath === "/" || urlPath === "/index.html") {
    return path.join(publicDir, "index.html");
  }

  const vendorMap = {
    "/vendor/xterm.css": path.join(__dirname, "node_modules", "@xterm", "xterm", "css", "xterm.css"),
    "/vendor/xterm.js": path.join(__dirname, "node_modules", "@xterm", "xterm", "lib", "xterm.js"),
    "/vendor/xterm-addon-fit.js": path.join(
      __dirname,
      "node_modules",
      "@xterm",
      "addon-fit",
      "lib",
      "addon-fit.js"
    ),
  };
  if (vendorMap[urlPath]) {
    return vendorMap[urlPath];
  }

  return safePublicPath(urlPath);
}

function hmac(value) {
  return crypto.createHmac("sha256", sessionSecret).update(value).digest("base64url");
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left));
  const rightBuffer = Buffer.from(String(right));
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function createSession(username) {
  const payload = Buffer.from(
    JSON.stringify({
      username,
      expiresAt: Date.now() + sessionTtlSeconds * 1000,
    })
  ).toString("base64url");
  return `${payload}.${hmac(payload)}`;
}

function parseCookies(header) {
  return Object.fromEntries(
    String(header || "")
      .split(";")
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => {
        const separator = entry.indexOf("=");
        if (separator === -1) {
          return [entry, ""];
        }
        return [entry.slice(0, separator), decodeURIComponent(entry.slice(separator + 1))];
      })
  );
}

function readSession(req) {
  if (!loginRequired()) {
    return { username: "arcade" };
  }

  const cookie = parseCookies(req.headers.cookie)[sessionCookieName];
  if (!cookie) {
    return null;
  }

  const [payload, signature] = cookie.split(".");
  if (!payload || !signature || !safeEqual(signature, hmac(payload))) {
    return null;
  }

  try {
    const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    if (!session.username || Number(session.expiresAt) < Date.now()) {
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

function isAuthenticatedRequest(req) {
  return readSession(req) !== null;
}

function sessionCookie(username) {
  return [
    `${sessionCookieName}=${encodeURIComponent(createSession(username))}`,
    "HttpOnly",
    "SameSite=Strict",
    "Path=/",
    `Max-Age=${sessionTtlSeconds}`,
  ].join("; ");
}

function expiredSessionCookie() {
  return `${sessionCookieName}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`;
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 4096) {
        reject(new Error("Request too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

async function handleLogin(req, res) {
  let body;
  try {
    body = await readJsonBody(req);
  } catch {
    sendJson(res, 400, { ok: false, error: "Richiesta non valida." });
    return;
  }

  const username = String(body.username || "").trim();
  const submittedCode = String(body.accessCode || "");
  const normalizedUser = username.toLowerCase();
  if (!username) {
    sendJson(res, 400, { ok: false, error: "Inserisci uno username." });
    return;
  }
  if (allowedUsers.size > 0 && !allowedUsers.has(normalizedUser)) {
    sendJson(res, 403, { ok: false, error: "Username non autorizzato." });
    return;
  }
  if (accessCode && !safeEqual(submittedCode, accessCode)) {
    sendJson(res, 403, { ok: false, error: "Codice di accesso non valido." });
    return;
  }

  sendJson(
    res,
    200,
    { ok: true, username },
    {
      "Set-Cookie": sessionCookie(username),
    }
  );
}

function handleSession(req, res) {
  const session = readSession(req);
  sendJson(res, 200, {
    authenticated: session !== null,
    loginRequired: loginRequired(),
    username: session ? session.username : "",
  });
}

function handleLogout(res) {
  sendJson(res, 200, { ok: true }, { "Set-Cookie": expiredSessionCookie() });
}

function spawnConsole(cols, rows) {
  return pty.spawn(
    "powershell.exe",
    [
      "-NoLogo",
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      runScript,
      "-AppDir",
      appDir,
      "-StateDir",
      stateDir,
    ],
    {
      name: "xterm-256color",
      cols: cols || 100,
      rows: rows || 32,
      cwd: appDir,
      env: {
        ...process.env,
        CONSOLE_GG_STATS_PATH: path.join(stateDir, "console_gg_stats.json"),
        PYTHONIOENCODING: "utf-8",
        PYTHONDONTWRITEBYTECODE: "1",
      },
    }
  );
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  if (url.pathname === "/health") {
    sendJson(res, 200, { ok: true, appDir, stateDir, loginRequired: loginRequired() });
    return;
  }
  if (url.pathname === "/session") {
    handleSession(req, res);
    return;
  }
  if (url.pathname === "/login" && req.method === "POST") {
    handleLogin(req, res);
    return;
  }
  if (url.pathname === "/logout" && req.method === "POST") {
    handleLogout(res);
    return;
  }

  sendFile(res, resolveAssetPath(url.pathname));
});

const wss = new WebSocketServer({ noServer: true });
server.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  if (url.pathname !== "/ws") {
    socket.write("HTTP/1.1 404 Not Found\r\n\r\n");
    socket.destroy();
    return;
  }
  if (!isAuthenticatedRequest(req)) {
    socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
    socket.destroy();
    return;
  }

  wss.handleUpgrade(req, socket, head, (ws) => {
    wss.emit("connection", ws, req);
  });
});

wss.on("connection", (socket, request) => {
  if (!isAuthenticatedRequest(request)) {
    socket.close(1008, "Login required");
    return;
  }

  const terminal = spawnConsole(100, 32);

  terminal.onData((data) => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "output", data }));
    }
  });

  terminal.onExit(({ exitCode }) => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "exit", exitCode }));
      socket.close();
    }
  });

  socket.on("message", (payload) => {
    let message;
    try {
      message = JSON.parse(payload.toString());
    } catch {
      return;
    }

    if (message.type === "input" && typeof message.data === "string") {
      terminal.write(message.data);
    }

    if (message.type === "resize") {
      const cols = Math.max(20, Math.min(240, Number(message.cols) || 100));
      const rows = Math.max(10, Math.min(80, Number(message.rows) || 32));
      terminal.resize(cols, rows);
    }
  });

  socket.on("close", () => {
    terminal.kill();
  });
});

server.listen(port, host, () => {
  console.log(`Console GG arcade web listening on http://${host}:${port}`);
  console.log(`App dir: ${appDir}`);
  console.log(`State dir: ${stateDir}`);
  console.log(
    loginRequired()
      ? `Allowed users: ${allowedUsers.size ? [...allowedUsers].join(", ") : "access-code only"}`
      : "Login gate disabled. Set CONSOLE_GG_ALLOWED_USERS to enable it."
  );
});
