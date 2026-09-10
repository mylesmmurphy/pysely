let runtime;
async function initialize() {
  const { loadPyodide } = await import("https://cdn.jsdelivr.net/pyodide/v314.0.6/full/pyodide.mjs");
  const python = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.6/full/" });
  await python.loadPackage("micropip");
  const wheel = new URL("../wheels/pysely-0.1.0.dev0-py3-none-any.whl", self.location).href;
  await python.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheel)}, deps=False)`);
  const [bridge, database] = await Promise.all([
    fetch(new URL("playground.py?build=3", self.location)),
    fetch(new URL("examples/database.py", self.location)),
  ]);
  if (!bridge.ok || !database.ok) throw new Error("Could not load playground support");
  await python.runPythonAsync(await bridge.text());
  return { python, database: await database.text() };
}
self.onmessage = async ({ data }) => {
  try {
    runtime ??= initialize();
    const { python, database } = await runtime;
    const evaluate = python.globals.get("evaluate_playground");
    try {
      self.postMessage({ id: data.id, ...JSON.parse(evaluate(data.schema, database, data.query, data.dialect)) });
    } finally { evaluate.destroy(); }
  } catch (error) {
    self.postMessage({ id: data.id, error: String(error) });
  }
};
