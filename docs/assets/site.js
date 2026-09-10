(() => {
  const title = document.querySelector(".md-header__topic:first-child .md-ellipsis");
  const logo = document.querySelector('[data-md-component="logo"]');
  if (!title || !logo || title.closest("a")) return;

  const link = document.createElement("a");
  link.className = "pysely-home-link";
  link.href = logo.href;
  title.replaceWith(link);
  link.append(title);
})();
