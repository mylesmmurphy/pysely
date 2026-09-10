(() => {
  const script = document.createElement("script");
  script.src = new URL("playground.js?build=14", document.currentScript.src);
  document.head.append(script);
})();
