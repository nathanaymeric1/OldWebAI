import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.join(__dirname, "_site");
const port = Number(process.env.PORT || 3000);
const apiKey = process.env.OPENROUTER_API_KEY;
const model = process.env.OPENROUTER_MODEL || "openrouter/free";
const siteUrl = process.env.SITE_URL || `http://localhost:${port}`;
const siteName = process.env.SITE_NAME || "OldWeb AI";

if (!apiKey) {
  console.warn("Warning: OPENROUTER_API_KEY is not set.");
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "POST" && req.url === "/api/chat") {
      return handleChat(req, res);
    }

    return serveStatic(req, res);
  } catch (error) {
    console.error(error);
    sendJson(res, 500, { error: "Internal server error." });
  }
});

server.listen(port, () => {
  console.log(`OldWeb AI running at http://localhost:${port}`);
});

async function handleChat(req, res) {
  if (!apiKey) {
    return sendJson(res, 500, {
      error: "OPENROUTER_API_KEY is not configured on the server."
    });
  }

  const body = await readJson(req);
  const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
  const temperature = Number(body.temperature);

  if (!prompt) {
    return sendJson(res, 400, { error: "Prompt is required." });
  }

  if (!Number.isFinite(temperature) || temperature < 0 || temperature > 2) {
    return sendJson(res, 400, { error: "Temperature must be between 0 and 2." });
  }

  const openRouterResponse = await fetch(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": siteUrl,
        "X-Title": siteName
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
        temperature
      })
    }
  );

  const data = await openRouterResponse.json();

  if (!openRouterResponse.ok) {
    console.error("OpenRouter error:", data);
    return sendJson(res, openRouterResponse.status, {
      error: data?.error?.message || "OpenRouter request failed."
    });
  }

  const reply = data?.choices?.[0]?.message?.content;
  const actualModel = data?.model || model;

  if (!reply) {
    return sendJson(res, 502, {
      error: "OpenRouter returned no text response."
    });
  }

  return sendJson(res, 200, {
    reply,
    model: actualModel
  });
}

async function serveStatic(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    return sendJson(res, 405, { error: "Method not allowed." });
  }

  let requestPath = decodeURIComponent((req.url || "/").split("?")[0]);
  if (requestPath === "/") requestPath = "/index.html";

  const absolutePath = path.resolve(siteRoot, `.${requestPath}`);

  if (!absolutePath.startsWith(path.resolve(siteRoot))) {
    return sendJson(res, 403, { error: "Forbidden." });
  }

  try {
    const file = await fs.readFile(absolutePath);
    const ext = path.extname(absolutePath).toLowerCase();

    const types = {
      ".html": "text/html; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".json": "application/json; charset=utf-8",
      ".svg": "image/svg+xml",
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".ico": "image/x-icon"
    };

    res.writeHead(200, {
      "Content-Type": types[ext] || "application/octet-stream"
    });

    if (req.method === "HEAD") return res.end();
    return res.end(file);
  } catch {
    return sendJson(res, 404, { error: "Not found." });
  }
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "";

    req.on("data", chunk => {
      raw += chunk;
      if (raw.length > 100_000) {
        req.destroy();
        reject(new Error("Request too large."));
      }
    });

    req.on("end", () => {
      try {
        resolve(JSON.parse(raw || "{}"));
      } catch {
        reject(new Error("Invalid JSON."));
      }
    });

    req.on("error", reject);
  });
}

function sendJson(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8"
  });
  res.end(JSON.stringify(payload));
}
