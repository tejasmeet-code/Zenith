import { spawn, execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  process.stdout.write(line);
  try {
    fs.appendFileSync(path.resolve('./bot.log'), line);
  } catch (_) {}
}

log('==============================================');
log('🚀 Launching ZyroX / Zenith Discord Bot');
log('==============================================');

// Find Python binary
const possibleVenvs = [
  path.resolve('./.venv/bin/python3'),
  '/home/container/.venv/bin/python3',
  process.env.VIRTUAL_ENV ? path.join(process.env.VIRTUAL_ENV, 'bin/python3') : null,
  '/usr/local/bin/python3',
  '/usr/bin/python3',
  'python3'
].filter(Boolean);

let pythonBin = 'python3';
for (const p of possibleVenvs) {
  if (fs.existsSync(p)) {
    pythonBin = p;
    break;
  }
}

log(`🐍 Selected Python Binary: ${pythonBin}`);

// Start HTTP web server on port 3000
const port = parseInt(process.env.PORT || process.env.SERVER_PORT || '3000', 10);

const server = http.createServer((req, res) => {
  if (req.url === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'online',
      bot: 'ZyroX',
      uptime: process.uptime(),
      timestamp: new Date().toISOString()
    }));
    return;
  }

  // Dashboard status page
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>ZyroX Bot & Dashboard</title>
      <style>
        :root {
          --bg-dark: #0b0d12;
          --card-bg: #141824;
          --card-border: #232a3b;
          --accent: #5865F2;
          --accent-hover: #4752C4;
          --text-main: #f0f2f5;
          --text-muted: #8e99b0;
          --success: #57F287;
        }
        body {
          background-color: var(--bg-dark);
          color: var(--text-main);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 1rem;
        }
        .container {
          background: var(--card-bg);
          border: 1px solid var(--card-border);
          border-radius: 16px;
          padding: 2.5rem;
          max-width: 560px;
          width: 100%;
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6);
          text-align: center;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 1.5rem;
        }
        .title {
          font-size: 2rem;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
          background: linear-gradient(135deg, #7289da, #5865F2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .subtitle {
          color: var(--text-muted);
          font-size: 0.95rem;
          margin-bottom: 2rem;
          line-height: 1.6;
        }
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 2rem;
        }
        .metric-card {
          background: #0f121a;
          border: 1px solid var(--card-border);
          border-radius: 10px;
          padding: 1rem;
        }
        .metric-value {
          font-size: 1.4rem;
          font-weight: 700;
          color: var(--success);
        }
        .metric-label {
          font-size: 0.8rem;
          color: var(--text-muted);
          margin-top: 4px;
        }
        .btn-group {
          display: flex;
          gap: 12px;
          justify-content: center;
        }
        .btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 0.75rem 1.25rem;
          border-radius: 8px;
          font-weight: 600;
          text-decoration: none;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }
        .btn-primary {
          background: var(--accent);
          color: #fff;
        }
        .btn-primary:hover {
          background: var(--accent-hover);
        }
        .btn-secondary {
          background: #1c2233;
          color: var(--text-main);
          border: 1px solid var(--card-border);
        }
        .btn-secondary:hover {
          background: #252d44;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 class="title">ZyroX All-In-One Bot</h1>
        </div>
        <p class="subtitle">
          Next-Generation Discord Bot Engine with Lavalink Music, Antinuke, Moderation, and Next.js Web Dashboard Integration.
        </p>

        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">Active</div>
            <div class="metric-label">Gateway Status</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">Online</div>
            <div class="metric-label">Lavalink Music</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">Enabled</div>
            <div class="metric-label">Emoji Sync</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">v5.0.0</div>
            <div class="metric-label">System Version</div>
          </div>
        </div>

        <div class="btn-group">
          <a href="https://discord.gg/codexdev" target="_blank" class="btn btn-primary">Join Support Server</a>
          <a href="/api/health" class="btn btn-secondary">API Health Check</a>
        </div>
      </div>
    </body>
    </html>
  `);
});

server.listen(port, '0.0.0.0', () => {
  log(`Listening on port ${port}`);
  log(`Server listening on port ${port}`);
  log(`Ready! Bot & Web service running.`);
});

// Launch Python bot
const botCwd = path.resolve('./bot');
log(`🤖 Spawning ZyroX bot process in cwd: ${botCwd} ...`);

const bot = spawn(pythonBin, ['CodeX.py'], {
  cwd: botCwd,
  env: {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    brand_name: 'ZyroX',
    NEXT_PUBLIC_BRAND_NAME: 'ZyroX'
  }
});

bot.stdout.on('data', (d) => {
  const str = d.toString();
  log(`[BOT STDOUT] ${str}`);
});

bot.stderr.on('data', (d) => {
  const str = d.toString();
  log(`[BOT STDERR] ${str}`);
});

bot.on('error', (err) => {
  log(`❌ Failed to start Python bot process: ${err.message}`);
});

bot.on('exit', (code, signal) => {
  log(`⚠️ Bot process exited with code ${code} / signal ${signal}`);
  setTimeout(() => process.exit(code || 0), 5000);
});
