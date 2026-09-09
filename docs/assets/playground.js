const pyselyWheel = "/wheels/pysely-0.1.0.dev0-py3-none-any.whl";
let pyselyRuntime;

async function loadPysely() {
  if (!pyselyRuntime) {
    pyselyRuntime = (async () => {
      const wheelUrl = new URL(pyselyWheel, window.location.origin).href;
      const runtime = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.6/full/",
      });
      await runtime.loadPackage("micropip");
      await runtime.runPythonAsync(
        `import micropip\nawait micropip.install(${JSON.stringify(wheelUrl)}, deps=False)`,
      );
      return runtime;
    })();
  }
  return pyselyRuntime;
}

document.addEventListener("click", async (event) => {
  if (!event.target.closest("#playground-run")) return;

  const button = document.querySelector("#playground-run");
  const code = document.querySelector("#playground-code");
  const dialect = document.querySelector("#playground-dialect");
  const output = document.querySelector("#playground-output");
  const status = document.querySelector("#playground-status");

  button.disabled = true;
  status.textContent = "Loading Python…";

  try {
    const runtime = await loadPysely();
    status.textContent = "Running…";
    const result = await runtime.runPythonAsync(
      `playground_dialect = ${JSON.stringify(dialect.value)}\n${code.value}`,
    );
    const value = result?.toJs
      ? result.toJs({ dict_converter: Object.fromEntries })
      : result;
    result?.destroy?.();
    output.textContent = JSON.stringify(value, null, 2);
    status.textContent = "Complete";
  } catch (error) {
    output.textContent = String(error);
    status.textContent = "Error";
  } finally {
    button.disabled = false;
  }
});
