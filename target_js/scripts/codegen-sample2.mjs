#!/usr/bin/env node
/**
 * Pipe sample2.cum → AST → ast_to_js.py and write target_js/test/sample2.mjs
 * (replaces the former CMake custom_command).
 */

import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const PYTHON = process.env.PYTHON ?? "python3";
const GEN = join(ROOT, "generator");
const CUM = join(ROOT, "sample2.cum");
const OUT = join(ROOT, "target_js/test/sample2.mjs");

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, {
    encoding: "utf-8",
    maxBuffer: 16 * 1024 * 1024,
    ...opts,
  });
  if (r.error) throw r.error;
  if ((r.status ?? 1) !== 0) {
    if (r.stderr) process.stderr.write(r.stderr);
    process.exit(r.status ?? 1);
  }
  return r;
}

const ast = run(PYTHON, [join(GEN, "cum_to_ast.py"), CUM], {
  cwd: ROOT,
  env: { ...process.env, PYTHONPATH: GEN },
});

const js = run(PYTHON, [join(GEN, "ast_to_js.py")], {
  cwd: ROOT,
  env: { ...process.env, PYTHONPATH: GEN },
  input: ast.stdout,
});

writeFileSync(OUT, js.stdout);
console.error("wrote %s (%d bytes)", OUT, Buffer.byteLength(js.stdout));
