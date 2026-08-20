#!/usr/bin/env node
import fs from 'node:fs';
import { FoundationSchemas } from '../generated/typescript/index.mjs';

const args = process.argv.slice(2);
const expectFail = args[0] === '--expect-fail';
const [fixturePath, schemaName] = expectFail ? args.slice(1) : args;

if (!fixturePath || !schemaName) {
  console.error('usage: validate_zod.mjs [--expect-fail] <fixture.json> <schemaName>');
  process.exit(2);
}

const schema = FoundationSchemas[schemaName];
if (!schema) {
  console.error(`unknown schema: ${schemaName}`);
  process.exit(2);
}

const value = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const result = schema.safeParse(value);

if (expectFail) {
  if (result.success) {
    console.error(`${fixturePath} unexpectedly passed ${schemaName}`);
    process.exit(1);
  }
  console.log(`${fixturePath} failed ${schemaName} as expected`);
  process.exit(0);
}

if (!result.success) {
  console.error(JSON.stringify(result.error.issues, null, 2));
  process.exit(1);
}

console.log(JSON.stringify(result.data));
