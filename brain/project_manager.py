from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from brain.capabilities.web_builder import WebBuilderCapability, ProjectResult


ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT / "projects" / "generated"
CURRENT_FILE = PROJECTS_DIR / ".current"


class ProjectManager:
    @property
    def project_dir(self):
        """Absolute path to the currently active generated project."""
        current = self.current_path()
        return current.resolve() if current else (PROJECTS_DIR / "current").resolve()


    def __init__(self) -> None:
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        self.builder = WebBuilderCapability()

    @staticmethod
    def slugify(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = value.strip("-")
        return value or "klyor-project"

    def current_name(self) -> str | None:
        if not CURRENT_FILE.exists():
            return None

        value = CURRENT_FILE.read_text(encoding="utf-8").strip()
        return value or None

    def current_path(self) -> Path | None:
        name = self.current_name()
        if not name:
            return None

        path = PROJECTS_DIR / name

        if not path.exists() or not path.is_dir():
            return None

        return path

    def current_project(self) -> dict | None:
        """Compatibility view for older runtime callers."""
        path = self.current_path()
        if path is None:
            return None
        return {"name": self.current_name(), "path": str(path)}

    def set_current(self, name: str) -> None:
        CURRENT_FILE.write_text(name, encoding="utf-8")

    def reset(self) -> None:
        """Completely remove the active project and its generated files."""
        current = self.current_path()

        if current is not None and current.exists():
            shutil.rmtree(current, ignore_errors=True)

        # Also remove any stale generated project directories.
        # There is intentionally no persistent project memory yet.
        if PROJECTS_DIR.exists():
            for child in PROJECTS_DIR.iterdir():
                if child.name == ".current":
                    continue
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)

        if CURRENT_FILE.exists():
            CURRENT_FILE.unlink()

    def build(self, prompt: str) -> dict:
        result: ProjectResult | None = self.builder.build(prompt)

        if result is None:
            return {
                "success": False,
                "message": "I couldn't identify a website or browser-game request.",
            }

        slug = self.slugify(result.name)

        project_dir = PROJECTS_DIR / slug

        if project_dir.exists():
            shutil.rmtree(project_dir)

        project_dir.mkdir(parents=True, exist_ok=True)

        files = []

        for generated_file in result.files:
            file_path = project_dir / generated_file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                generated_file.content,
                encoding="utf-8",
            )

            files.append(generated_file.path)

        metadata = {
            "name": result.name,
            "slug": slug,
            "project_type": result.project_type,
            "description": result.description,
            "files": files,
        }

        (project_dir / "project.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        validation = self.validate(project_dir)
        if not validation["valid"]:
            shutil.rmtree(project_dir)
            return {
                "success": False,
                "message": "Generated project validation failed: " + "; ".join(validation["errors"]),
                "validation": validation,
            }

        self.set_current(slug)

        return {
            "success": True,
            "name": result.name,
            "slug": slug,
            "project_type": result.project_type,
            "description": result.description,
            "files": files,
            "validation": validation,
        }

    @staticmethod
    def validate(project_dir: Path) -> dict:
        required = ("index.html", "styles.css", "script.js")
        errors = []

        for filename in required:
            path = project_dir / filename
            if not path.is_file():
                errors.append(f"missing {filename}")
                continue
            try:
                path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                errors.append(f"unreadable {filename}")

        html_path = project_dir / "index.html"
        script_path = project_dir / "script.js"
        html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        if html and "<html" not in html.lower():
            errors.append("index.html has no html root")

        if html:
            if 'href="styles.css"' not in html:
                errors.append("index.html does not reference styles.css")
            if 'src="script.js"' not in html:
                errors.append("index.html does not reference script.js")
            if html.lower().count("<html") != html.lower().count("</html>"):
                errors.append("index.html has unbalanced html tags")

            anchors = set(re.findall(r'href="#([^"/]+)"', html))
            ids = set(re.findall(r'id="([^"]+)"', html))
            missing_anchors = sorted(anchor for anchor in anchors if anchor not in ids)
            errors.extend(f"missing internal link target #{anchor}" for anchor in missing_anchors)

        if script_path.is_file() and shutil.which("node"):
            result = subprocess.run(
                ["node", "--check", str(script_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                errors.append("script.js syntax error: " + (result.stderr.strip() or "unknown error"))

        return {"valid": not errors, "errors": errors}

    def context(self) -> dict:
        project = self.current_path()
        status = self.status()
        if project is None:
            return {"project": status, "files": {}, "validation": {"valid": False, "errors": ["no active project"]}}

        files = {
            relative: self.read_file(relative) or ""
            for relative in status["files"]
        }
        return {
            "project": status,
            "files": files,
            "validation": self.validate(project),
        }

    def read_file(self, relative_path: str) -> str | None:
        project = self.current_path()

        if project is None:
            return None

        requested = (project / relative_path).resolve()

        if not requested.is_relative_to(project.resolve()):
            return None

        if not requested.is_file():
            return None

        return requested.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> bool:
        project = self.current_path()

        if project is None:
            return False

        requested = (project / relative_path).resolve()

        if not requested.is_relative_to(project.resolve()):
            return False

        requested.parent.mkdir(parents=True, exist_ok=True)
        requested.write_text(content, encoding="utf-8")
        return True

    def modify(self, prompt: str) -> dict:
        project = self.current_path()

        if project is None:
            return {
                "success": False,
                "message": "There is no active project yet.",
            }

        lowered = prompt.lower()

        html = self.read_file("index.html") or ""
        css = self.read_file("styles.css") or ""
        js = self.read_file("script.js") or ""

        changed = []
        contact_already_present = False

        # TITLE / NAME CHANGES
        title_match = re.search(
            r"(?:change|rename|set|make)\s+(?:the\s+)?(?:site\s+)?(?:title|name)\s+(?:to|as)\s+[\"']?([^\"']+?)[\"']?$",
            prompt,
            re.IGNORECASE,
        )

        if title_match:
            new_title = title_match.group(1).strip().rstrip(".")
            html = re.sub(
                r"<title>.*?</title>",
                f"<title>{new_title}</title>",
                html,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )

            html = re.sub(
                r"(<h1[^>]*>).*?(</h1>)",
                rf"\1{new_title}\2",
                html,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )

            self.write_file("index.html", html)
            changed.append("index.html")

        # BLACK BUTTONS
        if (
            "button" in lowered
            and "black" in lowered
            and any(word in lowered for word in ("make", "change", "set"))
        ):
            css += """

/* Klyor modification */
button,
.btn,
.button,
a.button {
    background: #000 !important;
    color: #fff !important;
}
"""

            self.write_file("styles.css", css)
            changed.append("styles.css")

        # CONTACT SECTION
        if "contact" in lowered and any(
            word in lowered
            for word in ("add", "create", "include", "make")
        ):
            if "id=\"contact\"" not in html:
                section = """
<section id="contact" class="contact-section">
    <div class="container">
        <p class="eyebrow">Contact</p>
        <h2>Let's work together.</h2>
        <p>Have a project in mind? Send a message.</p>

        <form id="contact-form">
            <input type="text" name="name" placeholder="Your name" required>
            <input type="email" name="email" placeholder="Your email" required>
            <textarea name="message" placeholder="Your message" required></textarea>
            <button type="submit">Send message</button>
        </form>
    </div>
</section>
"""

                html = html.replace("</main>", section + "\n</main>")

                css += """

/* Klyor modification */
.contact-section {
    padding: 96px 24px;
}

.contact-section .container {
    max-width: 760px;
    margin: 0 auto;
}

.contact-section form {
    display: grid;
    gap: 14px;
    margin-top: 28px;
}

.contact-section input,
.contact-section textarea {
    width: 100%;
    padding: 14px 16px;
    border: 1px solid #ddd;
    border-radius: 12px;
    font: inherit;
}

.contact-section textarea {
    min-height: 140px;
    resize: vertical;
}
"""

                self.write_file("index.html", html)
                self.write_file("styles.css", css)

                changed.extend(["index.html", "styles.css"])
            else:
                contact_already_present = True

        # BIGGER HERO
        if "hero" in lowered and any(
            word in lowered
            for word in ("bigger", "larger", "increase", "better", "prominent", "stronger", "improve")
        ):
            css += """

/* Klyor modification */
.hero {
    min-height: 90vh;
    display: flex;
    align-items: center;
}

.hero h1 {
    max-width: 12ch;
    text-wrap: balance;
}

.hero .hero-lede,
.hero > p {
    max-width: 52ch;
}
"""

            self.write_file("styles.css", css)
            changed.append("styles.css")

        # HEADING SCALE
        if "heading" in lowered and any(
            word in lowered for word in ("bigger", "larger", "increase")
        ):
            css += """

/* Klyor modification */
h1,
h2 {
    font-size: clamp(2.5rem, 8vw, 6rem);
}
"""
            self.write_file("styles.css", css)
            changed.append("styles.css")

        # RESPONSIVE
        if "responsive" in lowered:
            css += """

/* Klyor modification */
@media (max-width: 700px) {
    .container {
        width: min(100% - 32px, 1100px);
    }

    nav {
        flex-wrap: wrap;
        gap: 12px;
    }

    h1 {
        font-size: clamp(2.4rem, 12vw, 5rem);
    }

    .hero {
        min-height: auto;
        padding: 80px 0;
    }
}
"""

            self.write_file("styles.css", css)
            changed.append("styles.css")

        # Add one accessible inline SVG icon without introducing a dependency.
        if "svg" in lowered or "icon" in lowered or "icons" in lowered:
            if "klyor-icon" not in html:
                icon = (
                    '<svg class="klyor-icon" viewBox="0 0 24 24" '
                    'aria-hidden="true"><path d="M12 3l2.7 5.3L20 11l-5.3 2.7L12 19l-2.7-5.3L4 11l5.3-2.7L12 3z" '
                    'fill="none" stroke="currentColor" stroke-width="1.8"/></svg>'
                )
                html = html.replace(
                    '<a class="logo"',
                    f'<a class="logo">{icon}</a><a class="logo"',
                    1,
                )
                css += """
.klyor-icon {
    width: 1em;
    height: 1em;
    vertical-align: -0.12em;
    margin-right: 0.35em;
}
"""
                self.write_file("index.html", html)
                self.write_file("styles.css", css)
                changed.extend(["index.html", "styles.css"])

        if "footer" in lowered and any(word in lowered for word in ("add", "create", "include")):
            if 'class="site-footer"' not in html:
                html = html.replace(
                    "</body>",
                    '<footer class="site-footer"><p>Built with care.</p></footer>\n</body>',
                    1,
                )
                self.write_file("index.html", html)
                changed.append("index.html")

        if "spacing" in lowered or "cleaner" in lowered or "professional" in lowered:
            css += """

/* Klyor modification */
:root {
    --klyor-space: clamp(1rem, 3vw, 3rem);
}

section {
    scroll-margin-top: 88px;
}

button,
a {
    transition: transform 180ms ease, opacity 180ms ease, background 180ms ease;
}

button:hover,
a:hover {
    opacity: 0.86;
}
"""
            self.write_file("styles.css", css)
            changed.append("styles.css")

        # SIMPLE ANIMATIONS
        if "animation" in lowered or "animations" in lowered:
            css += """

/* Klyor modification */
@keyframes klyor-fade-up {
    from {
        opacity: 0;
        transform: translateY(18px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero,
section {
    animation: klyor-fade-up 0.6s ease both;
}
"""

            self.write_file("styles.css", css)
            changed.append("styles.css")

        changed = list(dict.fromkeys(changed))

        if not changed:
            if contact_already_present:
                return {
                    "success": True,
                    "modified": [],
                    "message": "The current project already has a contact section.",
                    "project": self.current_name(),
                }
            return {
                "success": False,
                "message": (
                    "I understand that you want to modify the current project, "
                    "but I don't have a safe local transformation for that request yet."
                ),
            }

        return {
            "success": True,
            "modified": changed,
            "message": f"Updated {', '.join(changed)}.",
            "project": self.current_name(),
            "validation": self.validate(project),
        }

    def status(self) -> dict:
        project = self.current_path()

        if project is None:
            return {
                "exists": False,
                "name": None,
                "files": [],
            }

        metadata = project / "project.json"

        if metadata.exists():
            try:
                data = json.loads(metadata.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

        files = []

        for path in sorted(project.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "project.json":
                continue
            files.append(str(path.relative_to(project)))

        return {
            "exists": True,
            "name": data.get("name", self.current_name()),
            "slug": self.current_name(),
            "project_type": data.get("project_type", "website"),
            "description": data.get("description", ""),
            "files": files,
        }

    def reset(self) -> None:
        name = self.current_name()

        if name:
            project = PROJECTS_DIR / name
            if project.exists():
                shutil.rmtree(project)

        if CURRENT_FILE.exists():
            CURRENT_FILE.unlink()


project_manager = ProjectManager()
