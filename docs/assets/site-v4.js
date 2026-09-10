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

  const slugs = new Set();
  const slugify = value => value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  for (const set of document.querySelectorAll(".tabbed-set")) {
    const labels = set.querySelectorAll(":scope > .tabbed-labels > label");
    const block = set.parentElement?.closest(".tabbed-block");
    const outerSet = block?.parentElement?.closest(".tabbed-set");
    let prefix = "";

    if (block && outerSet) {
      const blocks = [...block.parentElement.children].filter(child =>
        child.classList.contains("tabbed-block")
      );
      const outerLabels = outerSet.querySelectorAll(":scope > .tabbed-labels > label");
      prefix = slugify(outerLabels[blocks.indexOf(block)]?.textContent || "");
    }

    for (const label of labels) {
      const input = document.getElementById(label.htmlFor);
      if (!input) continue;

      const base = [prefix, slugify(label.textContent || "")].filter(Boolean).join("-");
      let slug = base;
      let suffix = 2;
      while (slugs.has(slug)) slug = `${base}-${suffix++}`;
      slugs.add(slug);

      input.id = slug;
      label.htmlFor = slug;
    }
  }

  const selected = document.getElementById(location.hash.slice(1));
  if (selected?.matches('.tabbed-set > input[type="radio"]')) selected.click();
};

if (typeof document$ !== "undefined") document$.subscribe(enhancePage);
else enhancePage();
