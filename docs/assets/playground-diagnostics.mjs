const before = (a, b) => a.line < b.line || (a.line === b.line && a.character <= b.character);
const contains = (outer, inner) => before(outer.start, inner.start) && before(inner.end, outer.end);
const sameStart = (a, b) => a.start.line === b.start.line && a.start.character === b.start.character;

export function groupDiagnostics(diagnostics, uri) {
  const parents = new Map();
  const calls = diagnostics.filter(item => item.code === "reportCallIssue");
  for (const call of calls) {
    const argument = diagnostics.find(item => item.code === "reportArgumentType" && contains(call.range, item.range));
    if (argument) parents.set(call, argument);
  }
  for (const item of diagnostics) {
    if (item.code !== "reportUnknownMemberType") continue;
    const call = calls.find(call => sameStart(item.range, call.range) && contains(item.range, call.range));
    if (call) parents.set(item, parents.get(call) || call);
  }
  return diagnostics.filter(item => !parents.has(item)).map(item => {
    const relatedInformation = [...(item.relatedInformation || [])];
    const message = item.message.split("\n")[0];
    if (message !== item.message) {
      relatedInformation.push({ location: { uri, range: item.range }, message: item.message });
    }
    for (const [child, parent] of parents) {
      if (parent === item) relatedInformation.push({ location: { uri, range: child.range }, message: child.message });
    }
    return { ...item, message, relatedInformation };
  });
}
