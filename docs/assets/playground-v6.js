(() => {
  const script = document.createElement("script");
  script.src = new URL("playground.js?build=7", document.currentScript.src);
  document.head.append(script);
})();
