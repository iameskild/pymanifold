// This file is invoked by make_models.py...
// It is copied to manifold/common and run from there
// this generates the JSON schemas for the Manifold API found in schema.ts

import * as fs from 'fs';
import * as path from 'path';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { API } from './src/api/schema';

async function generateJsonSchemas() {
  console.log('Using local schema.ts');

  // Convert each schema in API to JSON schema
  for (const [endpointPath, endpoint] of Object.entries(API)) {
    const schema = endpoint.props;
    if (schema instanceof z.ZodType) {
      const jsonSchema = zodToJsonSchema(schema, {
        name: endpointPath,
        $refStrategy: 'root', // for recursive references
      });

      const sanitizedPath = endpointPath
        // Replace path parameters like ':betId' with '{betId}'
        .replace(/:([^/]+)/g, '{$1}')
        .split('/');

      const directories = sanitizedPath.slice(0, -1);
      const fileName = sanitizedPath[sanitizedPath.length - 1] || 'index';
      const outputDir = path.join('../../schemas', ...directories);
      const outputPath = path.join(outputDir, `${fileName}.json`);

      fs.mkdirSync(outputDir, { recursive: true });
      fs.writeFileSync(outputPath, JSON.stringify(jsonSchema, null, 2));

      console.log(`Generated schema for ${endpointPath}`);
    } else {
      console.warn(`No valid Zod schema found for ${endpointPath}`);
    }
  }
}

generateJsonSchemas().catch((error) => {
  console.error(error);
  process.exit(1);
});
