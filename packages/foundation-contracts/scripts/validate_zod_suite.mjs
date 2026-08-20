#!/usr/bin/env node
import fs from 'node:fs';
import { FoundationSchemas } from '../generated/typescript/index.mjs';

const mode = process.argv[2];
if (!['valid', 'invalid'].includes(mode)) {
  console.error('usage: validate_zod_suite.mjs <valid|invalid>');
  process.exit(2);
}

const suite = JSON.parse(fs.readFileSync('fixtures/v1/fixture-suite.v1.json', 'utf8'));

function pointer(value, ptr) {
  if (!ptr) return value;
  return ptr.split('/').slice(1).reduce((current, part) => current[part], value);
}

let count = 0;
for (const entry of suite[mode]) {
  const [fixturePath, schemaName, jsonPointer] = entry;
  const schema = FoundationSchemas[schemaName];
  if (!schema) {
    console.error(`unknown schema: ${schemaName}`);
    process.exit(2);
  }
  const value = pointer(JSON.parse(fs.readFileSync(fixturePath, 'utf8')), jsonPointer);
  const result = schema.safeParse(value);
  if (mode === 'valid' && !result.success) {
    console.error(`${fixturePath}${jsonPointer ?? ''} failed ${schemaName}`);
    console.error(JSON.stringify(result.error.issues, null, 2));
    process.exit(1);
  }
  if (mode === 'invalid' && result.success) {
    console.error(`${fixturePath}${jsonPointer ?? ''} unexpectedly passed ${schemaName}`);
    process.exit(1);
  }
  count += 1;
}

console.log(`${mode} Zod fixture suite PASS (${count})`);
