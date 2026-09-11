(() => {
  const scriptUrl = new URL(document.currentScript.src);
  const assets = new URL(".", scriptUrl);
  const revision = scriptUrl.pathname.match(/playground\.([^.]+)\.js$/)?.[1] || "dev";
  const assetUrl = path => {
    const url = new URL(path, assets);
    url.searchParams.set("v", revision);
    return url;
  };
  const monacoBase = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs";
  let loading;
  let mountVersion = 0;
  let cleanup = () => {};

  class LspClient {
    constructor(worker, files) {
      this.worker = worker;
      this.files = files;
      this.nextId = 0;
      this.pending = new Map();
      this.diagnostics = () => {};
      this.settings = { python: { analysis: {
        // Pyright's default. Strict adds "type of X is unknown" follow-on
        // errors across the whole chain after one failed call, which buries
        // the argument-level diagnostic users need.
        typeCheckingMode: "standard",
        diagnosticMode: "openFilesOnly",
        extraPaths: ["/site-packages"],
        typeshedPaths: ["/typeshed-fallback"],
      } } };
      worker.addEventListener("message", event => this.receive(event.data));
    }

    receive(message) {
      if (message.type) return;
      if (message.id !== undefined && (message.result !== undefined || message.error)) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result);
        return;
      }
      if (message.id !== undefined) {
        let result = null;
        if (message.method === "workspace/configuration") {
          result = (message.params?.items || []).map(item => {
            if (!item.section) return this.settings;
            return item.section.split(".").reduce((value, key) => value?.[key], this.settings) || {};
          });
        } else if (message.method === "workspace/workspaceFolders") {
          result = [{ uri: "file:///workspace", name: "Pysely playground" }];
        }
        this.worker.postMessage({ jsonrpc: "2.0", id: message.id, result });
        return;
      }
      if (message.method === "textDocument/publishDiagnostics") this.diagnostics(message.params);
    }

    request(method, params, token) {
      const id = ++this.nextId;
      const promise = new Promise((resolve, reject) => {
        this.pending.set(id, { resolve, reject });
        this.worker.postMessage({ jsonrpc: "2.0", id, method, params });
      });
      token?.onCancellationRequested(() => {
        this.worker.postMessage({ jsonrpc: "2.0", method: "$/cancelRequest", params: { id } });
      });
      return promise;
    }

    notify(method, params) {
      this.worker.postMessage({ jsonrpc: "2.0", method, params });
    }

    async initialize() {
      await this.request("initialize", {
        processId: null,
        rootUri: "file:///workspace",
        workspaceFolders: [{ uri: "file:///workspace", name: "Pysely playground" }],
        capabilities: {
          workspace: { configuration: true, workspaceFolders: true },
          textDocument: {
            completion: { contextSupport: true, completionItem: { snippetSupport: true, documentationFormat: ["markdown", "plaintext"], insertReplaceSupport: true, resolveSupport: { properties: ["documentation", "detail", "additionalTextEdits"] } } },
            hover: { contentFormat: ["markdown", "plaintext"] },
            publishDiagnostics: { versionSupport: true, relatedInformation: true, tagSupport: { valueSet: [1, 2] } },
            signatureHelp: { signatureInformation: { documentationFormat: ["markdown", "plaintext"], parameterInformation: { labelOffsetSupport: true } } },
            definition: { linkSupport: true },
          },
        },
        initializationOptions: {},
      });
      this.notify("initialized", {});
      this.notify("workspace/didChangeConfiguration", { settings: this.settings });
    }

    open(model) {
      this.notify("textDocument/didOpen", { textDocument: {
        uri: model.uri.toString(), languageId: "python", version: model.getVersionId(), text: model.getValue(),
      } });
    }

    change(model) {
      this.notify("textDocument/didChange", {
        textDocument: { uri: model.uri.toString(), version: model.getVersionId() },
        contentChanges: [{ text: model.getValue() }],
      });
    }

    close(model) {
      this.notify("textDocument/didClose", { textDocument: { uri: model.uri.toString() } });
    }

    // database.py is written by `pysely codegen`, not by hand. The playground
    // regenerates it from the schema editor on every run and pushes it here so
    // Pyright checks the interface the schema actually produces.
    updateGenerated(text) {
      if (typeof text !== "string" || this.generated === text) return;
      const uri = "file:///workspace/database.py";
      const version = (this.generatedVersion = (this.generatedVersion || 0) + 1);
      if (this.generated === undefined) {
        this.notify("textDocument/didOpen", { textDocument: { uri, languageId: "python", version, text } });
      } else {
        this.notify("textDocument/didChange", { textDocument: { uri, version }, contentChanges: [{ text }] });
      }
      this.generated = text;
      this.files["workspace/database.py"] = text;
    }

    textRequest(method, model, position, token, extra = {}) {
      return this.request(method, {
        textDocument: { uri: model.uri.toString() },
        position: { line: position.lineNumber - 1, character: position.column - 1 },
        ...extra,
      }, token);
    }

    dispose() {
      for (const pending of this.pending.values()) pending.reject(new Error("Pyright stopped"));
      this.pending.clear();
      this.worker.terminate();
    }
  }

  const lspRange = range => ({
    startLineNumber: range.start.line + 1,
    startColumn: range.start.character + 1,
    endLineNumber: range.end.line + 1,
    endColumn: range.end.character + 1,
  });

  const markdown = value => typeof value === "string" ? value : value?.value || "";

  async function startIntelligence(monaco, models, status, retry) {
    const startedAt = performance.now();
    let client;
    let worker;
    const disposables = [];
    const readonlyModels = [];
    status.textContent = "Loading Python suggestions";
    status.setAttribute("aria-busy", "true");
    retry.hidden = true;
    try {
      const [manifestResponse, typeshedResponse] = await Promise.all([
        fetch(assetUrl("intelligence/manifest.json")),
        fetch(assetUrl("intelligence/typeshed-fallback.zip")),
      ]);
      if (!manifestResponse.ok || !typeshedResponse.ok) throw new Error("Could not load Pyright assets");
      const manifest = await manifestResponse.json();
      const typeshed = await typeshedResponse.arrayBuffer();
      const files = {
        ...manifest.files,
        "workspace/schema.py": models[0].getValue(),
        "workspace/query.py": models[1].getValue(),
      };
      worker = new Worker(assetUrl("intelligence/pyright-worker.js"));
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("Pyright startup timed out")), 20000);
        const onMessage = event => {
          if (event.data.type === "loaded") {
            worker.postMessage({ type: "bootstrap", files, typeshed }, [typeshed]);
          } else if (event.data.type === "ready") {
            clearTimeout(timeout);
            worker.removeEventListener("message", onMessage);
            resolve();
          } else if (event.data.type === "failed") {
            clearTimeout(timeout);
            reject(new Error(event.data.message));
          }
        };
        worker.addEventListener("message", onMessage);
        worker.addEventListener("error", event => reject(new Error(`${event.message} (${event.filename}:${event.lineno}:${event.colno})`)), { once: true });
      });
      client = new LspClient(worker, files);
      client.diagnostics = params => {
        const model = monaco.editor.getModel(monaco.Uri.parse(params.uri));
        if (!model || (params.version && params.version < model.getVersionId())) return;
        monaco.editor.setModelMarkers(model, "pyright", params.diagnostics.map(item => ({
          ...lspRange(item.range), message: item.message, code: item.code,
          severity: [0, monaco.MarkerSeverity.Error, monaco.MarkerSeverity.Warning, monaco.MarkerSeverity.Info, monaco.MarkerSeverity.Hint][item.severity || 4],
          tags: item.tags,
          relatedInformation: item.relatedInformation?.map(info => ({
            resource: monaco.Uri.parse(info.location.uri),
            ...lspRange(info.location.range), message: info.message,
          })),
        })));
      };
      await client.initialize();
      models.slice(0, 2).forEach(model => client.open(model));

      const owned = model => model.uri.path.startsWith("/workspace/");
      disposables.push(monaco.languages.registerCompletionItemProvider("python", {
        triggerCharacters: [".", "[", "\"", "'"],
        provideCompletionItems: async (model, position, context, token) => {
          if (!owned(model)) return { suggestions: [] };
          const version = model.getVersionId();
          const result = await client.textRequest("textDocument/completion", model, position, token, { context: {
            triggerKind: context.triggerKind, triggerCharacter: context.triggerCharacter,
          } });
          if (!result || version !== model.getVersionId()) return { suggestions: [] };
          const source = Array.isArray(result) ? { items: result, isIncomplete: false } : result;
          return { incomplete: source.isIncomplete, suggestions: source.items.map(item => {
            const edit = item.textEdit;
            const range = edit?.insert && edit?.replace
              ? { insert: lspRange(edit.insert), replace: lspRange(edit.replace) }
              : edit?.range ? lspRange(edit.range) : undefined;
            return {
              label: item.label, kind: item.kind || monaco.languages.CompletionItemKind.Text,
              detail: item.detail, documentation: markdown(item.documentation), sortText: item.sortText,
              filterText: item.filterText, insertText: edit?.newText || item.insertText || item.label,
              range, commitCharacters: item.commitCharacters,
              insertTextRules: item.insertTextFormat === 2 ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet : undefined,
              additionalTextEdits: item.additionalTextEdits?.map(textEdit => ({ range: lspRange(textEdit.range), text: textEdit.newText })),
              _lsp: item,
            };
          }) };
        },
        resolveCompletionItem: async (item, token) => {
          if (!item._lsp) return item;
          const resolved = await client.request("completionItem/resolve", item._lsp, token);
          return { ...item, detail: resolved.detail, documentation: markdown(resolved.documentation) };
        },
      }));
      disposables.push(monaco.languages.registerHoverProvider("python", {
        provideHover: async (model, position, token) => {
          if (!owned(model)) return null;
          const result = await client.textRequest("textDocument/hover", model, position, token);
          if (!result) return null;
          const contents = Array.isArray(result.contents) ? result.contents : [result.contents];
          return { range: result.range && lspRange(result.range), contents: contents.map(item => ({ value: markdown(item) })) };
        },
      }));
      disposables.push(monaco.languages.registerSignatureHelpProvider("python", {
        signatureHelpTriggerCharacters: ["(", ","],
        provideSignatureHelp: async (model, position, token, context) => {
          if (!owned(model)) return null;
          const value = await client.textRequest("textDocument/signatureHelp", model, position, token, { context });
          return value ? { value, dispose() {} } : null;
        },
      }));
      disposables.push(monaco.languages.registerDefinitionProvider("python", {
        provideDefinition: async (model, position, token) => {
          if (!owned(model)) return null;
          const result = await client.textRequest("textDocument/definition", model, position, token);
          if (!result) return null;
          const definitions = Array.isArray(result) ? result : [result];
          return definitions.map(item => {
            const uri = item.targetUri || item.uri;
            const path = monaco.Uri.parse(uri).path.slice(1);
            if (!monaco.editor.getModel(monaco.Uri.parse(uri)) && files[path] !== undefined) {
              readonlyModels.push(monaco.editor.createModel(files[path], "python", monaco.Uri.parse(uri)));
            }
            return item.targetUri
              ? { uri: monaco.Uri.parse(uri), range: lspRange(item.targetRange), targetSelectionRange: lspRange(item.targetSelectionRange), originSelectionRange: item.originSelectionRange && lspRange(item.originSelectionRange) }
              : { uri: monaco.Uri.parse(uri), range: lspRange(item.range) };
          });
        },
      }));
      models.slice(0, 2).forEach(model => disposables.push(model.onDidChangeContent(() => client.change(model))));
      status.textContent = `Python suggestions ready · Pyright ${manifest.pyrightVersion}`;
      status.setAttribute("aria-busy", "false");
      status.dataset.startupMs = String(Math.round(performance.now() - startedAt));
      return {
        update: text => client.updateGenerated(text),
        dispose: () => {
          models.slice(0, 2).forEach(model => client.close(model));
          disposables.forEach(item => item.dispose());
          readonlyModels.forEach(model => model.dispose());
          client.dispose();
        },
      };
    } catch (failure) {
      client?.dispose();
      if (!client) worker?.terminate();
      disposables.forEach(item => item.dispose());
      status.textContent = `Python suggestions unavailable · ${failure.message || failure}`;
      status.setAttribute("aria-busy", "false");
      retry.hidden = false;
      throw failure;
    }
  }

  function loadEditor() {
    loading ??= new Promise((resolve, reject) => {
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
        window.require(["vs/editor/editor.main"], resolve, reject);
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
        loadEditor(), fetch(assetUrl("examples/schema.py")), fetch(assetUrl("examples/query.py")),
      ]);
      if (!root.isConnected || version !== mountVersion) return;
      if (!schemaResponse.ok || !queryResponse.ok) throw new Error("Could not load the example files");
      const examples = await Promise.all([schemaResponse.text(), queryResponse.text()]);
      const monaco = window.monaco;
      const options = { automaticLayout: true, minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false,
        scrollbar: { alwaysConsumeMouseWheel: false, vertical: "visible", horizontal: "visible", verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
        padding: { top: 12 }, tabSize: 4, wordWrap: "on", fixedOverflowWidgets: true,
        quickSuggestions: { other: true, comments: false, strings: true }, wordBasedSuggestions: "off" };
      const schemaUri = monaco.Uri.parse("file:///workspace/schema.py");
      const queryUri = monaco.Uri.parse("file:///workspace/query.py");
      monaco.editor.getModel(schemaUri)?.dispose();
      monaco.editor.getModel(queryUri)?.dispose();
      const models = [
        monaco.editor.createModel(examples[0], "python", schemaUri),
        monaco.editor.createModel(examples[1], "python", queryUri),
        monaco.editor.createModel("", "sql"),
      ];
      for (const name of ["schema", "query", "sql"]) root.querySelector(`#playground-${name}`).textContent = "";
      const editors = ["schema", "query", "sql"].map((name, index) => monaco.editor.create(
        root.querySelector(`#playground-${name}`), { ...options, model: models[index], readOnly: index === 2, ariaLabel: `${name} editor` },
      ));
      const fitEditors = () => {
        if (window.innerWidth <= 1000) {
          root.style.removeProperty("--pysely-editor-height");
          return;
        }
        const top = root.querySelector("#playground-query").getBoundingClientRect().top;
        const parametersHeight = root.querySelector(".pysely-playground__parameters").getBoundingClientRect().height;
        const height = Math.max(260, Math.min(640, window.innerHeight - top - parametersHeight - 16));
        root.style.setProperty("--pysely-editor-height", `${height}px`);
      };
      fitEditors();
      window.addEventListener("resize", fitEditors);
      const theme = () => monaco.editor.setTheme(document.body.dataset.mdColorScheme === "slate" ? "vs-dark" : "vs");
      theme();
      const observer = new MutationObserver(theme);
      observer.observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
      const runButton = root.querySelector("#playground-run");
      const stopButton = root.querySelector("#playground-stop");
      const dialect = root.querySelector("#playground-dialect");
      const codegenStatus = root.querySelector("#playground-codegen-status");
      const intelligenceStatus = root.querySelector("#playground-intelligence-status");
      const intelligenceRetry = root.querySelector("#playground-intelligence-retry");
      let stopIntelligence = () => {};
      let pushGenerated = () => {};
      let generated;
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
        status.textContent = worker ? "Compiling" : "Loading Python";
        status.setAttribute("aria-busy", "true");
        codegenStatus.textContent = "database.py: regenerating…";
        delete codegenStatus.dataset.fresh;
        error.hidden = true;
        if (!worker) {
          worker = new Worker(assetUrl("playground-worker.js"), { type: "module" });
          worker.onmessage = ({ data }) => {
            if (data.id !== id) return;
            busy = false;
            runButton.disabled = false;
            stopButton.disabled = true;
            status.setAttribute("aria-busy", "false");
            if (data.database) {
              const first = generated === undefined;
              const changed = data.database !== generated;
              generated = data.database;
              pushGenerated(generated);
              codegenStatus.textContent = first
                ? "database.py: generated from schema.py"
                : changed ? "database.py: regenerated from schema.py" : "database.py: up to date";
              if (changed && !first) codegenStatus.dataset.fresh = "";
            } else {
              codegenStatus.textContent = "database.py: not regenerated (fix schema.py)";
            }
            if (data.error) {
              status.textContent = "Check your code";
              error.textContent = data.error;
              error.hidden = false;
              models[2].setValue("-- Fix the error to compile this query.");
              root.querySelector("#playground-parameters").textContent = "[]";
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
            status.setAttribute("aria-busy", "false");
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
        status.setAttribute("aria-busy", "false");
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
      const loadIntelligence = () => {
        stopIntelligence();
        pushGenerated = () => {};
        return startIntelligence(monaco, models, intelligenceStatus, intelligenceRetry)
          .then(intelligence => {
            if (!root.isConnected || version !== mountVersion) intelligence.dispose();
            else {
              stopIntelligence = intelligence.dispose;
              pushGenerated = intelligence.update;
              if (generated) pushGenerated(generated);
            }
          })
          .catch(failure => { console.error("Could not start Pyright", failure); });
      };
      intelligenceRetry.onclick = loadIntelligence;
      cleanup = () => { stop(); stopIntelligence(); pushGenerated = () => {}; observer.disconnect(); window.removeEventListener("resize", fitEditors); subscriptions.forEach(item => item.dispose()); editors.forEach(editor => editor.dispose()); models.forEach(model => model.dispose()); };
      setTimeout(() => loadIntelligence().finally(run), 500);
    } catch (failure) {
      status.textContent = "Could not load playground";
      status.setAttribute("aria-busy", "false");
      error.textContent = String(failure);
      error.hidden = false;
    }
  }
  if (typeof document$ !== "undefined") document$.subscribe(mount);
  else mount();
})();
