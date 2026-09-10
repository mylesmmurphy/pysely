const enhancePage = () => {
  const title = document.querySelector(".md-header__topic:first-child .md-ellipsis");
  const logo = document.querySelector('[data-md-component="logo"]');
  if (title && logo && !title.closest("a")) {
    const link = document.createElement("a");
    link.className = "pysely-home-link";
    link.href = logo.href;
    title.replaceWith(link);
    link.append(title);
  }

  for (const link of document.querySelectorAll(".md-footer__link")) {
    link.querySelector(".md-footer__direction")?.setAttribute("aria-hidden", "true");
    if (link.classList.contains("md-footer__link--next")) {
      link.classList.add("md-footer__link--primary");
    }
    if (!new URL(link.href).pathname.endsWith("/playground/")) continue;
    link.classList.add("md-footer__link--playground", "md-footer__link--primary");
    link.setAttribute("aria-label", "Open the interactive playground editor");
    link.querySelector(".md-ellipsis").textContent = "Open playground editor";
  }
};

if (typeof document$ !== "undefined") document$.subscribe(enhancePage);
else enhancePage();
