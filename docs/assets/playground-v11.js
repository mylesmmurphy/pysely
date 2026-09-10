(() => {
  const script = document.createElement("script");
  script.src = new URL("playground.js?build=13", document.currentScript.src);
  document.head.append(script);
})();
