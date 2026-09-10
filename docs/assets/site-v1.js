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
    if (!new URL(link.href).pathname.endsWith("/playground/")) continue;
    link.classList.add("md-footer__link--playground");
    link.setAttribute("aria-label", "Open the interactive playground editor");
    link.querySelector(".md-footer__direction").textContent = "Interactive editor";
    link.querySelector(".md-ellipsis").textContent = "Open playground";
  }
};

if (typeof document$ !== "undefined") document$.subscribe(enhancePage);
else enhancePage();
