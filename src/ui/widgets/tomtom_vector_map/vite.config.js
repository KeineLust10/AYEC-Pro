import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

const projectRoot = fileURLToPath(new URL('../../../../', import.meta.url));

export default defineConfig({
  root: fileURLToPath(new URL('./web', import.meta.url)),
  base: './',
  build: {
    outDir: resolve(projectRoot, 'assets/tomtom_vector_map'),
    emptyOutDir: true,
    target: 'es2022',
  },
});
