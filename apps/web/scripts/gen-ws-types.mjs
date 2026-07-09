// @ts-check
// Deterministic generator for the WebSocket message types (CONTRACT A2).
//
// Reads apps/server/ws-protocol.json (the server's single source of truth,
// `TypeAdapter(WsMessage).json_schema()` + a protocol version), emits:
//   - src/api/ws-types.gen.ts       — the discriminated WsMessage union + members
//   - src/api/ws-protocol.gen.ts    — export const WS_PROTOCOL_VERSION
//
// No timestamps are written, so `make web-clients` twice yields an empty diff.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const protocolPath = resolve(webRoot, "../server/ws-protocol.json");
const typesOut = resolve(webRoot, "src/api/ws-types.gen.ts");
const versionOut = resolve(webRoot, "src/api/ws-protocol.gen.ts");

const BANNER = [
  "/* eslint-disable */",
  "// @generated",
  "// This file is auto-generated from apps/server/ws-protocol.json by",
  "// scripts/gen-ws-types.mjs. Do NOT edit by hand — run `make web-clients`.",
];

const doc = JSON.parse(readFileSync(protocolPath, "utf8"));

const ts = await compile(doc.message, "WsMessage", {
  additionalProperties: false,
  bannerComment: BANNER.join("\n"),
  format: false,
  declareExternallyReferenced: true,
  enableConstEnums: false,
  unreachableDefinitions: true,
});

writeFileSync(typesOut, ts.endsWith("\n") ? ts : `${ts}\n`);

const version = doc.ws_protocol_version;
if (typeof version !== "number" || !Number.isInteger(version)) {
  throw new Error(
    `ws-protocol.json ws_protocol_version must be an integer, got: ${String(version)}`,
  );
}
const versionFile = [
  ...BANNER,
  "",
  `export const WS_PROTOCOL_VERSION = ${version} as const;`,
  "",
].join("\n");
writeFileSync(versionOut, versionFile);

console.log(
  `wrote ${typesOut} and ${versionOut} (ws_protocol_version=${version})`,
);
