const menuButton = document.querySelector(".menu-toggle");
const nav = document.querySelector("#site-nav");
menuButton?.addEventListener("click", () => { const open = nav.classList.toggle("open"); menuButton.setAttribute("aria-expanded", String(open)); });
nav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => { nav.classList.remove("open"); menuButton?.setAttribute("aria-expanded", "false"); }));
document.querySelector("#contact-form")?.addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; if (!form.checkValidity()) { form.reportValidity(); return; } document.querySelector("#form-message").textContent = "Thanks. Your message is ready to send."; form.reset(); });
