import { expect, test } from "@playwright/test";

// @ts-ignore JavaScript module shared with the browser.
import { groupDiagnostics } from "../../docs/assets/playground-diagnostics.mjs";

const range = (line: number, start: number, endLine: number, end: number) => ({
  start: { line, character: start }, end: { line: endLine, character: end },
});
const diagnostic = (code: string, span: ReturnType<typeof range>, message = code) => ({ code, range: span, message });

test("keeps the argument range and groups errors from the failed call chain", () => {
  const call = diagnostic("reportCallIssue", range(5, 4, 6, 48));
  const argument = diagnostic("reportArgumentType", range(6, 16, 6, 22), "Invalid table\n  Expected TableName");
  const member = diagnostic("reportUnknownMemberType", range(5, 4, 7, 10));
  const unrelated = diagnostic("reportUnknownMemberType", range(12, 0, 12, 9));
  const result = groupDiagnostics([call, member, argument, unrelated], "file:///workspace/query.py");
  expect(result).toHaveLength(2);
  expect(result[0].range).toEqual(argument.range);
  expect(result[0].message).toBe("Invalid table");
  expect(result[0].relatedInformation.map((info: { message: string }) => info.message)).toEqual([
    argument.message, call.message, member.message,
  ]);
  expect(result[1].code).toBe(unrelated.code);
});

test("retains call errors when Pyright cannot identify an argument", () => {
  const call = diagnostic("reportCallIssue", range(5, 4, 6, 48));
  const member = diagnostic("reportUnknownMemberType", range(5, 4, 7, 10));
  const result = groupDiagnostics([call, member], "file:///workspace/query.py");
  expect(result).toHaveLength(1);
  expect(result[0].range).toEqual(call.range);
  expect(result[0].relatedInformation[0].message).toBe(member.message);
});
