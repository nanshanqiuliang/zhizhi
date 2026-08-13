import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(packageRoot, "../..");
const schemaPath = resolve(repositoryRoot, "docs/contracts/knowledge-tree-graph.v1.schema.json");
const outputPath = resolve(packageRoot, "src/generated/graph-v1.ts");

const schema = JSON.parse(await readFile(schemaPath, "utf8"));
const definitions = schema.$defs;

function union(name) {
  return definitions[name].enum.map((value) => JSON.stringify(value)).join(" | ");
}

const source = `/**
 * Generated from docs/contracts/knowledge-tree-graph.v1.schema.json.
 * Do not hand-edit. Re-run: pnpm --filter @knowledge-tree/contracts-ts generate
 */

export type UuidV7 = string;
export type Sha256 = \`sha256:\${string}\`;
export type Origin = ${union("Origin")};
export type ReviewState = ${union("ReviewState")};
export type EdgeType = ${union("EdgeType")};
export type LockDimension = ${union("LockDimension")};
export type AnchorStatus = ${definitions.Anchor.properties.status.enum
  .map((value) => JSON.stringify(value))
  .join(" | ")};
export type GraphPatchOperation = ${definitions.Operation.oneOf
  .map((entry) => definitions[entry.$ref.split("/").at(-1)].properties.op.const)
  .map((value) => JSON.stringify(value))
  .join(" | ")};

export const graphContractSchemaVersion = 1 as const;
`;

if (process.argv.includes("--check")) {
  const current = await readFile(outputPath, "utf8").catch(() => "");
  if (current !== source) {
    process.stderr.write(
      "generated_contract_drift: run pnpm --filter @knowledge-tree/contracts-ts generate\n",
    );
    process.exitCode = 1;
  }
} else {
  await writeFile(outputPath, source, "utf8");
}
