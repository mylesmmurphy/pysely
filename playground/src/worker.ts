import "./polyfills";

import { Zip } from "@zenfs/archives";
import { InMemory, configure, fs, resolveMountConfig } from "@zenfs/core";
import path from "path";
import { PyrightServer } from "pyright/packages/pyright-internal/src/server";
import {
  BrowserMessageReader,
  BrowserMessageWriter,
  createConnection,
} from "vscode-languageserver/browser";

type Files = Record<string, string>;
type Bootstrap = { type: "bootstrap"; files: Files; typeshed: ArrayBuffer };

function writeFiles(files: Files) {
  const encoder = new TextEncoder();
  for (const [name, contents] of Object.entries(files)) {
    const target = `/${name}`;
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, encoder.encode(contents));
  }
}

async function start(message: Bootstrap) {
  const workspace = await resolveMountConfig(InMemory);
  const metadata = workspace.metadata.bind(workspace);
  workspace.metadata = () => ({ ...metadata(), noResizableBuffers: true });
  await configure({
    mounts: {
      "/": workspace,
      "/typeshed-fallback": { backend: Zip, data: message.typeshed },
    },
  });
  fs.mkdirSync("/tmp", { recursive: true });
  fs.mkdirSync("/workspace", { recursive: true });
  writeFiles(message.files);
  self.postMessage({ type: "ready" });

  const reader = new BrowserMessageReader(self);
  const writer = new BrowserMessageWriter(self);
  const connection = createConnection(reader, writer);
  new PyrightServer(connection, 0);
}

self.postMessage({ type: "loaded" });
self.addEventListener("message", function bootstrap(event: MessageEvent<Bootstrap>) {
  if (event.data.type !== "bootstrap") return;
  self.removeEventListener("message", bootstrap);
  start(event.data).catch((error) => {
    self.postMessage({ type: "failed", message: error instanceof Error ? error.stack : String(error) });
  });
});
