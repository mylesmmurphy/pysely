import os from "os";

process.execArgv = [];
Object.defineProperty(process, "platform", { value: "browser" });
Object.defineProperty(os, "constants", { value: __os_constants });
os.platform = () => "browser";
os.homedir = () => "/";

const browserSetTimeout = self.setTimeout.bind(self);
const browserClearTimeout = self.clearTimeout.bind(self);

self.setTimeout = ((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
  const id = browserSetTimeout(handler, timeout, ...args);
  return Object.assign(id, { unref: () => undefined });
}) as typeof setTimeout;

self.clearTimeout = ((handle?: number | { valueOf(): number }) => {
  browserClearTimeout(Number(handle));
}) as typeof clearTimeout;

declare const __os_constants: object;
