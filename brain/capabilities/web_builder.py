from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GeneratedFile:
    path: str
    language: str
    content: str


@dataclass
class ProjectResult:
    name: str
    project_type: str
    description: str
    files: list[GeneratedFile]


class WebBuilderCapability:
    BUILD_TRIGGERS = (
        "build me",
        "build a",
        "build an",
        "create a website",
        "create an website",
        "make a website",
        "make me a website",
        "make an website",
        "build a website",
        "build an website",
        "create a webpage",
        "create a web page",
        "make a webpage",
        "make a web page",
        "build a web page",
        "build a browser game",
        "create a browser game",
        "make a browser game",
        "build me a browser game",
        "create a game",
        "make a game",
    )

    WEBSITE_WORDS = {
        "website",
        "webpage",
        "web",
        "landing",
        "portfolio",
        "site",
    }

    GAME_WORDS = {
        "game",
        "browser game",
        "clicker",
        "platformer",
        "arcade",
    }

    @classmethod
    def is_build_request(cls, prompt: str) -> bool:
        """
        Detect requests that explicitly ask Klyor to create or modify
        a website/browser project.

        Normal programming questions must stay in Chat.
        """
        text = prompt.lower().strip()

        if re.search(
          r"\b(?:build|create|make|design|code)\b(?:\s+\w+){0,5}\s+"
          r"(?:website|site|webpage|page|portfolio|landing page|browser game)\b",
          text,
        ):
          return True

        build_phrases = (
            "build me a website",
            "build a website",
            "make me a website",
            "make a website",
            "create me a website",
            "create a website",
            "build me an html",
            "make me an html",
            "create an html",
            "create html",
            "build html",
            "make html",
            "build a webpage",
            "make a webpage",
            "create a webpage",
            "build me a page",
            "make me a page",
            "create me a page",
            "build a web page",
            "make a web page",
            "create a web page",
            "build a browser game",
            "make a browser game",
            "create a browser game",
            "build me a site",
            "build a site",
            "make me a site",
            "make a site",
            "create me a site",
            "create a site",
            "build me a portfolio",
            "make me a portfolio",
            "create me a portfolio",
            "build a landing page",
            "make a landing page",
            "create a landing page",
            "can you code a landing page",
            "can you make a website",
        )

        modification_phrases = (
            "add a section",
            "add a contact",
            "add pricing",
            "change the hero",
            "change the title",
            "change the navigation",
            "make the buttons",
            "make it responsive",
            "add animations",
            "remove the section",
            "update the website",
            "modify the website",
            "edit the website",
        )

        return (
            any(phrase in text for phrase in build_phrases)
            or any(phrase in text for phrase in modification_phrases)
        )

    @classmethod
    def is_website_request(cls, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in cls.WEBSITE_WORDS)

    @classmethod
    def is_game_request(cls, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in cls.GAME_WORDS)

    @staticmethod
    def _extract_title(prompt: str, project_type: str) -> str:
        lowered = prompt.lower()

        quoted = re.search(r'["\']([^"\']{2,80})["\']', prompt)
        if quoted:
            return quoted.group(1).strip()

        called = re.search(
          r"\b(?:called|named)\s+[\"']?([A-Za-z][A-Za-z0-9 -]{1,60})[\"']?\s*$",
          prompt,
          re.IGNORECASE,
        )
        if called:
          return called.group(1).strip().rstrip(".").title()

        named = re.search(
          r"(?:build|create|make)\s+(?:me\s+)?(?:a\s+)?(.+?)\s+"
          r"(?:website|site|webpage|page|portfolio)\b",
          prompt,
          re.IGNORECASE,
        )
        if named:
          candidate = re.sub(
            r"^(?:an?|the)\s+",
            "",
            named.group(1).strip(),
            flags=re.IGNORECASE,
          )
          if candidate:
            return candidate.title()

        if "portfolio" in lowered:
            return "My Portfolio"

        if "game" in lowered:
            return "Klyor Game"

        if "landing" in lowered:
            return "Welcome"

        return "Klyor Website"

    @staticmethod
    def _extract_description(prompt: str) -> str:
        lowered = prompt.lower()

        if "portfolio" in lowered:
            return "A modern personal portfolio website."

        if "game" in lowered:
            return "A simple browser game generated by Klyor Brain."

        return "A website generated by Klyor Brain."

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "klyor-project"

    @staticmethod
    def _escape(value: str) -> str:
        return html.escape(value, quote=True)

    def build(self, prompt: str) -> ProjectResult:
        project_type = "game" if self.is_game_request(prompt) else "website"

        title = self._extract_title(prompt, project_type)
        description = self._extract_description(prompt)
        slug = self._slug(title)

        if project_type == "game":
            files = self._build_game(title, description)
        elif "portfolio" in prompt.lower() or title.lower() == "trevon":
          files = self._build_portfolio(title, description)
        else:
            files = self._build_website(title, description)

        return ProjectResult(
            name=slug,
            project_type=project_type,
            description=description,
            files=files,
        )

    def _build_portfolio(
        self,
        title: str,
        description: str,
    ) -> list[GeneratedFile]:
        safe_title = self._escape(title)
        safe_description = self._escape(description)
        index = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{safe_description}">
  <title>{safe_title} | Developer Portfolio</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <a class="logo" href="#top" aria-label="{safe_title} home">
      <svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 3 8l9 5 9-5-9-5Zm-7 9 7 4 7-4M5 16l7 4 7-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>{safe_title}</span>
    </a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Open navigation"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>
    <nav id="site-nav" aria-label="Main navigation"><a href="#about">About</a><a href="#skills">Skills</a><a href="#projects">Projects</a><a href="#contact">Contact</a></nav>
  </header>
  <main id="top">
    <section class="hero shell" aria-labelledby="hero-title"><div><p class="eyebrow">Developer · Builder · Problem solver</p><h1 id="hero-title">I build digital products with <em>clarity.</em></h1><p class="hero-lede">{safe_description} I turn thoughtful ideas into fast, accessible experiences made to last.</p><div class="hero-actions"><a class="button primary" href="#projects">View projects <span aria-hidden="true">↗</span></a><a class="button quiet" href="#contact">Let's talk</a></div></div><div class="code-window" role="img" aria-label="Developer code illustration"><div class="window-bar"><i></i><i></i><i></i><span>trevon.js</span></div><pre><code><b>const</b> ideas = <i>"worth building"</i>;

<b>function</b> makeItReal(ideas) {{
  <b>return</b> ideas.ship();
}}</code></pre></div></section>
    <section id="about" class="section shell"><p class="eyebrow">01 / About</p><div class="split"><h2>Making complex things feel simple.</h2><p>I care about the details people notice and the foundations they don't. My work balances expressive interfaces with dependable engineering.</p></div></section>
    <section id="skills" class="section shell"><p class="eyebrow">02 / Skills</p><div class="skill-grid"><article><span>01</span><h3>Frontend</h3><p>HTML, CSS, JavaScript, responsive systems, accessibility and interaction design.</p></article><article><span>02</span><h3>Backend</h3><p>Python, APIs, data flows and practical systems that stay understandable.</p></article><article><span>03</span><h3>Product thinking</h3><p>Clear structure, useful feedback and interfaces that respect people's time.</p></article></div></section>
    <section id="projects" class="section shell"><p class="eyebrow">03 / Selected projects</p><div class="project-list"><article><div><span>01 / Product</span><h3>Signal Desk</h3><p>A focused workspace for turning noisy information into clear next steps.</p></div><a href="#contact" aria-label="Ask about Signal Desk"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 17 10-10M8 7h9v9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></a></article><article><div><span>02 / Web</span><h3>Open Studio</h3><p>A lightweight publishing system designed around calm, readable content.</p></div><a href="#contact" aria-label="Ask about Open Studio"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 17 10-10M8 7h9v9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></a></article></div></section>
    <section id="contact" class="section shell"><p class="eyebrow">04 / Contact</p><div class="contact-grid"><div><h2>Have a good problem?</h2><p>Tell me what you're building and where it feels stuck.</p></div><form id="contact-form" novalidate><label for="name">Name</label><input id="name" name="name" autocomplete="name" required><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" required><label for="message">Message</label><textarea id="message" name="message" rows="4" required></textarea><button class="button primary" type="submit">Send message <span aria-hidden="true">↗</span></button><p id="form-message" role="status" aria-live="polite"></p></form></div></section>
  </main>
  <footer class="site-footer shell"><span>© 2026 {safe_title}</span><a href="#top">Back to top ↑</a></footer>
  <script src="script.js"></script>
</body>
</html>'''
        styles = '''@import url("https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;700;800&display=swap");
:root { --ink:#17211d; --muted:#63716b; --paper:#f5f7f2; --line:#dbe3dc; --accent:#d6f36a; --dark:#20332b; }
* { box-sizing:border-box; } html { scroll-behavior:smooth; } body { margin:0; color:var(--ink); background:var(--paper); font:1rem/1.6 Manrope,sans-serif; } a { color:inherit; }
.shell { width:min(1180px,calc(100% - 48px)); margin:auto; } .site-header { height:76px; display:flex; align-items:center; justify-content:space-between; width:min(1280px,calc(100% - 48px)); margin:auto; } .logo { display:inline-flex; align-items:center; gap:9px; text-decoration:none; font-weight:800; letter-spacing:-.04em; } .brand-mark { width:24px; color:#55795f; } nav { display:flex; gap:28px; font-size:.85rem; } nav a { color:var(--muted); text-decoration:none; } .menu-toggle { display:none; border:0; background:none; padding:8px; } .menu-toggle svg { width:22px; }
.hero { min-height:680px; display:grid; grid-template-columns:1.05fr .95fr; gap:8vw; align-items:center; } .eyebrow, .skill-grid span, .project-list span { color:#6d8a62; font:500 .72rem/1.2 "DM Mono",monospace; letter-spacing:.08em; text-transform:uppercase; } h1,h2,h3 { letter-spacing:-.06em; line-height:1.05; } h1 { max-width:700px; margin:22px 0; font-size:clamp(3.4rem,7vw,7.6rem); } h2 { max-width:680px; font-size:clamp(2.4rem,5vw,5rem); } h3 { font-size:1.45rem; } em { color:#6f9360; font-style:normal; } .hero-lede { max-width:540px; color:var(--muted); font-size:1.1rem; } .hero-actions { display:flex; gap:12px; margin-top:30px; } .button { display:inline-flex; align-items:center; justify-content:center; gap:12px; min-height:46px; padding:0 18px; border:1px solid transparent; border-radius:999px; font-weight:700; text-decoration:none; cursor:pointer; } .primary { background:var(--accent); } .quiet { border-color:var(--line); }
.code-window { overflow:hidden; border-radius:14px; background:var(--dark); color:#e1efe2; box-shadow:28px 28px 0 #e8eedf; transform:rotate(2deg); animation:float-in .8s ease both; } .window-bar { display:flex; align-items:center; gap:7px; padding:15px 18px; border-bottom:1px solid #40544a; color:#9db0a3; font: .7rem "DM Mono",monospace; } .window-bar i { width:8px; height:8px; border-radius:50%; background:var(--accent); } .window-bar span { margin-left:10px; } .code-window pre { margin:0; padding:30px; overflow:auto; font:.82rem/1.9 "DM Mono",monospace; } .code-window b { color:var(--accent); } .code-window i { color:#f8be83; }
.section { padding:130px 0; border-top:1px solid var(--line); } .split,.contact-grid { display:grid; grid-template-columns:1fr .7fr; gap:8vw; margin-top:38px; } .split p,.contact-grid p,.skill-grid p,.project-list p { color:var(--muted); } .skill-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:24px; margin-top:48px; } .skill-grid article { padding:28px 0; border-top:2px solid var(--ink); } .project-list { margin-top:48px; } .project-list article { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:30px 0; border-top:1px solid var(--line); } .project-list article:last-child { border-bottom:1px solid var(--line); } .project-list p { max-width:500px; } .project-list a { display:grid; place-items:center; width:46px; height:46px; border:1px solid var(--line); border-radius:50%; } .project-list svg { width:20px; } form { display:grid; gap:9px; } label { color:var(--muted); font:500 .72rem "DM Mono",monospace; text-transform:uppercase; } input,textarea { width:100%; margin-bottom:12px; padding:13px 14px; border:1px solid var(--line); border-radius:7px; background:transparent; color:var(--ink); font:inherit; } textarea { resize:vertical; } #form-message { color:#4f7a55; } .site-footer { display:flex; justify-content:space-between; padding:28px 0; border-top:1px solid var(--line); color:var(--muted); font-size:.8rem; } .site-footer a { text-decoration:none; }
@keyframes float-in { from { opacity:0; transform:translateY(20px) rotate(2deg); } to { opacity:1; transform:translateY(0) rotate(2deg); } } @media (max-width:760px) { .shell,.site-header { width:calc(100% - 32px); } .hero { min-height:auto; grid-template-columns:1fr; gap:48px; padding:72px 0 110px; } h1 { font-size:clamp(3rem,15vw,5rem); } .section { padding:84px 0; } .split,.contact-grid,.skill-grid { grid-template-columns:1fr; gap:24px; } .skill-grid { gap:0; } nav { display:none; position:absolute; top:68px; left:16px; right:16px; padding:18px; background:var(--paper); border:1px solid var(--line); flex-direction:column; z-index:20; } nav.open { display:flex; } .menu-toggle { display:block; } } @media (prefers-reduced-motion:reduce) { *,*:before,*:after { animation:none!important; scroll-behavior:auto!important; } }'''
        script = '''const menuButton = document.querySelector(".menu-toggle");
const nav = document.querySelector("#site-nav");
menuButton?.addEventListener("click", () => { const open = nav.classList.toggle("open"); menuButton.setAttribute("aria-expanded", String(open)); });
nav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => { nav.classList.remove("open"); menuButton?.setAttribute("aria-expanded", "false"); }));
document.querySelector("#contact-form")?.addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; if (!form.checkValidity()) { form.reportValidity(); return; } document.querySelector("#form-message").textContent = "Thanks. Your message is ready to send."; form.reset(); });
'''
        return [GeneratedFile("index.html", "html", index), GeneratedFile("styles.css", "css", styles), GeneratedFile("script.js", "javascript", script)]

    def _build_website(
        self,
        title: str,
        description: str,
    ) -> list[GeneratedFile]:
        safe_title = self._escape(title)
        safe_description = self._escape(description)

        index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <a class="logo" href="#top">{safe_title}</a>
    <nav>
      <a href="#features">Features</a>
      <a href="#contact">Contact</a>
    </nav>
  </header>

  <main id="top">
    <section class="hero">
      <p class="eyebrow">Built with Klyor Brain</p>
      <h1>{safe_title}</h1>
      <p>{safe_description}</p>
      <a class="button" href="#contact">Get started</a>
    </section>

    <section id="features" class="section">
      <h2>Built for the web.</h2>
      <div class="cards">
        <article>
          <h3>Fast</h3>
          <p>A lightweight generated experience.</p>
        </article>
        <article>
          <h3>Responsive</h3>
          <p>Designed to adapt to different screens.</p>
        </article>
        <article>
          <h3>Interactive</h3>
          <p>Powered by HTML, CSS and JavaScript.</p>
        </article>
      </div>
    </section>

    <section id="contact" class="section contact">
      <h2>Get in touch</h2>
      <form id="contact-form">
        <input type="email" placeholder="Your email" required>
        <button class="button" type="submit">Send</button>
      </form>
      <p id="form-message"></p>
    </section>
  </main>

  <footer>
    <p>Generated by Klyor Brain</p>
  </footer>

  <script src="script.js"></script>
</body>
</html>
"""

        styles = """* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #111;
  background: #fff;
}

.site-header {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 7vw;
  border-bottom: 1px solid #e5e5e5;
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, .94);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.logo {
  color: inherit;
  text-decoration: none;
  font-weight: 800;
}

nav {
  display: flex;
  gap: 24px;
}

nav a {
  color: #555;
  text-decoration: none;
}

.hero {
  min-height: 72vh;
  display: grid;
  align-content: center;
  justify-items: start;
  padding: 8vw;
  max-width: 1100px;
}

.eyebrow {
  font-size: .85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .12em;
}

.hero h1 {
  font-size: clamp(3rem, 9vw, 8rem);
  line-height: .92;
  margin: 12px 0 24px;
  letter-spacing: -.06em;
}

.hero p {
  max-width: 620px;
  font-size: 1.2rem;
  line-height: 1.6;
}

.button {
  display: inline-flex;
  border: 0;
  border-radius: 999px;
  padding: 13px 22px;
  margin-top: 18px;
  background: #111;
  color: #fff;
  text-decoration: none;
  cursor: pointer;
  font: inherit;
}

.section {
  padding: 90px 8vw;
}

.section h2 {
  font-size: clamp(2rem, 5vw, 4rem);
  margin-top: 0;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.cards article {
  padding: 28px;
  border: 1px solid #ddd;
  border-radius: 20px;
}

.contact form {
  display: flex;
  gap: 12px;
  max-width: 600px;
}

.contact input {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  border: 1px solid #ccc;
  border-radius: 12px;
  font: inherit;
}

footer {
  padding: 40px 8vw;
  border-top: 1px solid #e5e5e5;
  color: #666;
}

@media (max-width: 700px) {
  .site-header {
    padding: 0 20px;
  }

  nav {
    display: none;
  }

  .hero {
    padding: 80px 20px;
  }

  .section {
    padding: 60px 20px;
  }

  .cards {
    grid-template-columns: 1fr;
  }

  .contact form {
    flex-direction: column;
  }
}
"""

        script = """document
  .getElementById("contact-form")
  ?.addEventListener("submit", (event) => {
    event.preventDefault();

    const message = document.getElementById("form-message");

    if (message) {
      message.textContent = "Thanks — your message was received.";
    }
  });
"""

        return [
            GeneratedFile("index.html", "html", index),
            GeneratedFile("styles.css", "css", styles),
            GeneratedFile("script.js", "javascript", script),
        ]

    def _build_game(
        self,
        title: str,
        description: str,
    ) -> list[GeneratedFile]:
        safe_title = self._escape(title)
        safe_description = self._escape(description)

        index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="game">
    <p class="eyebrow">Klyor Brain</p>
    <h1>{safe_title}</h1>
    <p>{safe_description}</p>

    <div class="hud">
      <span>Score: <strong id="score">0</strong></span>
      <span>Time: <strong id="time">30</strong></span>
    </div>

    <div id="game-area" aria-label="Game area">
      <button id="target" type="button" aria-label="Target"></button>
    </div>

    <button id="restart" class="restart" type="button">Restart</button>
  </main>

  <script src="script.js"></script>
</body>
</html>
"""

        styles = """* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  font-family: system-ui, sans-serif;
  background: #fff;
  color: #111;
}

.game {
  width: min(900px, 92vw);
  text-align: center;
}

h1 {
  font-size: clamp(2.5rem, 7vw, 6rem);
  margin: 0;
}

.eyebrow {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .12em;
}

.hud {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin: 30px 0 16px;
}

#game-area {
  height: min(55vh, 520px);
  min-height: 320px;
  position: relative;
  overflow: hidden;
  border: 2px solid #111;
  border-radius: 24px;
  background: #f7f7f7;
}

#target {
  position: absolute;
  width: 60px;
  height: 60px;
  border: 0;
  border-radius: 50%;
  background: #111;
  cursor: pointer;
}

.restart {
  margin-top: 18px;
  padding: 12px 20px;
  border: 0;
  border-radius: 999px;
  background: #111;
  color: #fff;
  cursor: pointer;
}
"""

        script = """const area = document.getElementById("game-area");
const target = document.getElementById("target");
const scoreElement = document.getElementById("score");
const timeElement = document.getElementById("time");
const restart = document.getElementById("restart");

let score = 0;
let time = 30;
let timer = null;

function moveTarget() {
  const maxX = Math.max(0, area.clientWidth - target.offsetWidth);
  const maxY = Math.max(0, area.clientHeight - target.offsetHeight);

  target.style.left = `${Math.random() * maxX}px`;
  target.style.top = `${Math.random() * maxY}px`;
}

function start() {
  clearInterval(timer);

  score = 0;
  time = 30;

  scoreElement.textContent = score;
  timeElement.textContent = time;

  moveTarget();

  timer = setInterval(() => {
    time -= 1;
    timeElement.textContent = time;

    if (time <= 0) {
      clearInterval(timer);
      target.disabled = true;
      target.textContent = "Done";
    }
  }, 1000);

  target.disabled = false;
  target.textContent = "";
}

target.addEventListener("click", () => {
  if (time <= 0) return;

  score += 1;
  scoreElement.textContent = score;
  moveTarget();
});

restart.addEventListener("click", start);

start();
"""

        return [
            GeneratedFile("index.html", "html", index),
            GeneratedFile("styles.css", "css", styles),
            GeneratedFile("script.js", "javascript", script),
        ]
