(() => {
  const assets = new URL(".", document.currentScript.src);
  const monacoBase = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs";
  let loading;
  let mountVersion = 0;
  let cleanup = () => {};

  function loadEditor() {
    loading ??= new Promise((resolve, reject) => {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = `${monacoBase}/editor/editor.main.css`;
      const stylesReady = new Promise((stylesResolve, stylesReject) => {
        stylesheet.onload = stylesResolve;
        stylesheet.onerror = stylesReject;
      });
      document.head.append(stylesheet);
      const script = document.createElement("script");
      script.src = `${monacoBase}/loader.js`;
      script.onerror = () => reject(new Error("Could not load the code editor."));
      script.onload = () => {
        window.MonacoEnvironment = {
          getWorkerUrl: () => URL.createObjectURL(new Blob([
            `self.MonacoEnvironment={baseUrl:${JSON.stringify(monacoBase + "/../")}};importScripts(${JSON.stringify(monacoBase + "/base/worker/workerMain.js")});`,
          ], { type: "text/javascript" })),
        };
        window.require.config({ paths: { vs: monacoBase } });
        window.require(["vs/editor/editor.main"], () => stylesReady.then(resolve, reject), reject);
      };
      document.head.append(script);
    }).catch(error => {
      loading = undefined;
      throw error;
    });
    return loading;
  }

  async function mount() {
    const version = ++mountVersion;
    cleanup();
    const root = document.querySelector("#playground-workbench");
    if (!root) return;
    const status = root.querySelector("#playground-status");
    const error = root.querySelector("#playground-error");
    try {
      const [, schemaResponse, queryResponse] = await Promise.all([
        loadEditor(), fetch(new URL("examples/schema.py", assets)), fetch(new URL("examples/query.py", assets)),
      ]);
      if (!root.isConnected || version !== mountVersion) return;
      if (!schemaResponse.ok || !queryResponse.ok) throw new Error("Could not load the example files");
      const examples = await Promise.all([schemaResponse.text(), queryResponse.text()]);
      const monaco = window.monaco;
      const options = { automaticLayout: true, minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false,
        padding: { top: 12 }, tabSize: 4, wordWrap: "on", fixedOverflowWidgets: true,
        quickSuggestions: { other: true, comments: false, strings: true }, wordBasedSuggestions: "off" };
      const models = [
        monaco.editor.createModel(examples[0], "python", monaco.Uri.parse(`file:///schema-${version}.py`)),
        monaco.editor.createModel(examples[1], "python", monaco.Uri.parse(`file:///query-${version}.py`)),
        monaco.editor.createModel("-- Loading Python…", "sql"),
      ];
      for (const name of ["schema", "query", "sql"]) root.querySelector(`#playground-${name}`).textContent = "";
      const editors = ["schema", "query", "sql"].map((name, index) => monaco.editor.create(
        root.querySelector(`#playground-${name}`), { ...options, model: models[index], readOnly: index === 2, ariaLabel: `${name} editor` },
      ));
      const theme = () => monaco.editor.setTheme(document.body.dataset.mdColorScheme === "slate" ? "vs-dark" : "vs");
      theme();
      const observer = new MutationObserver(theme);
      observer.observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
      const runButton = root.querySelector("#playground-run");
      const stopButton = root.querySelector("#playground-stop");
      const dialect = root.querySelector("#playground-dialect");
      let worker;
      let id = 0;
      let timer;
      let busy = false;
      let pending = false;

      function run() {
        clearTimeout(timer);
        if (busy) { pending = true; return; }
        busy = true;
        runButton.disabled = true;
        stopButton.disabled = false;
        status.textContent = worker ? "Compiling…" : "Loading Python…";
        error.hidden = true;
        if (!worker) {
          worker = new Worker(new URL("playground-worker.js", assets), { type: "module" });
          worker.onmessage = ({ data }) => {
            if (data.id !== id) return;
            busy = false;
            runButton.disabled = false;
            stopButton.disabled = true;
            for (const model of models) monaco.editor.setModelMarkers(model, "pysely", []);
            if (data.error) {
              status.textContent = "Check your code";
              error.textContent = data.error;
              error.hidden = false;
              models[2].setValue("-- Fix the error to compile this query.");
              root.querySelector("#playground-parameters").textContent = "[]";
              const model = data.file === "schema.py" ? models[0] : models[1];
              const line = Math.min(data.line || 1, model.getLineCount());
              monaco.editor.setModelMarkers(model, "pysely", [{ startLineNumber: line, endLineNumber: line,
                startColumn: 1, endColumn: model.getLineMaxColumn(line), message: data.error, severity: monaco.MarkerSeverity.Error }]);
            } else {
              status.textContent = "Compiled";
              error.textContent = "";
              error.hidden = true;
              models[2].setValue(data.sql);
              root.querySelector("#playground-parameters").textContent = JSON.stringify(data.parameters);
            }
            if (pending) { pending = false; run(); }
          };
          worker.onerror = (event) => {
            stop();
            status.textContent = "Could not start Python";
            error.textContent = event.message;
            error.hidden = false;
          };
        }
        worker.postMessage({ id: ++id, schema: models[0].getValue(), query: models[1].getValue(), dialect: dialect.value });
      }

      function stop() {
        clearTimeout(timer);
        worker?.terminate();
        worker = undefined;
        busy = pending = false;
        runButton.disabled = false;
        stopButton.disabled = true;
        status.textContent = "Stopped";
      }

      const subscriptions = models.slice(0, 2).map(model => model.onDidChangeContent(() => {
        clearTimeout(timer);
        timer = setTimeout(run, 600);
      }));
      runButton.onclick = run;
      stopButton.onclick = stop;
      dialect.onchange = run;
      root.querySelector("#playground-reset").onclick = () => { stop(); models[0].setValue(examples[0]); models[1].setValue(examples[1]); run(); };
      editors[1].addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, run);
      cleanup = () => { stop(); observer.disconnect(); subscriptions.forEach(item => item.dispose()); editors.forEach(editor => editor.dispose()); models.forEach(model => model.dispose()); };
      requestAnimationFrame(() => requestAnimationFrame(run));
    } catch (failure) {
      status.textContent = "Could not load playground";
      error.textContent = String(failure);
      error.hidden = false;
    }
  }
  if (typeof document$ !== "undefined") document$.subscribe(mount);
  else mount();
})();
