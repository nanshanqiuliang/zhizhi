import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(packageRoot, "../..");

const graphSchemaPath = resolve(
  repositoryRoot,
  "docs/contracts/knowledge-tree-graph.v1.schema.json",
);
const graphOutputPath = resolve(packageRoot, "src/generated/graph-v1.ts");
const graphPythonOutputPath = resolve(
  repositoryRoot,
  "packages/contracts-py/src/knowledge_tree_contracts/_generated_graph_v1_schema.py",
);

const llmSchemaPath = resolve(repositoryRoot, "docs/contracts/llm.v1.schema.json");
const llmPythonOutputPath = resolve(
  repositoryRoot,
  "packages/contracts-py/src/knowledge_tree_contracts/_generated_llm_v1_schema.py",
);

async function pythonArtifact(schemaPath, variableName, docPath) {
  const schema = JSON.parse(await readFile(schemaPath, "utf8"));
  return `"""Generated from ${docPath}.

Do not hand-edit. Re-run: pnpm --filter @knowledge-tree/contracts-ts generate
"""

${variableName} = r"""${JSON.stringify(schema, null, 2)}"""
`;
}

const graphSchema = JSON.parse(await readFile(graphSchemaPath, "utf8"));
const definitions = graphSchema.$defs;

function union(name) {
  return definitions[name].enum.map((value) => JSON.stringify(value)).join(" | ");
}

const graphSource = `/**
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

const graphPythonSource = await pythonArtifact(
  graphSchemaPath,
  "GRAPH_V1_SCHEMA_JSON",
  "docs/contracts/knowledge-tree-graph.v1.schema.json",
);

// The LLM canonical contract (WORK-2026-007) currently generates only the
// Python runtime artifact. TypeScript enums will be generated when the Web
// layer consumes the LLM port (roadmap Step 8); until then no second enum
// source may be hand-maintained.
const llmPythonSource = await pythonArtifact(
  llmSchemaPath,
  "LLM_V1_SCHEMA_JSON",
  "docs/contracts/llm.v1.schema.json",
);

if (process.argv.includes("--check")) {
  const current = await readFile(graphOutputPath, "utf8").catch(() => "");
  const currentGraphPython = await readFile(graphPythonOutputPath, "utf8").catch(() => "");
  const currentLlmPython = await readFile(llmPythonOutputPath, "utf8").catch(() => "");
  if (current !== graphSource || currentGraphPython !== graphPythonSource || currentLlmPython !== llmPythonSource) {
    process.stderr.write(
      "generated_contract_drift: run pnpm --filter @knowledge-tree/contracts-ts generate\n",
    );
    process.exitCode = 1;
  }
} else {
  await writeFile(graphOutputPath, graphSource, "utf8");
  await writeFile(graphPythonOutputPath, graphPythonSource, "utf8");
  await writeFile(llmPythonOutputPath, llmPythonSource, "utf8");
}
