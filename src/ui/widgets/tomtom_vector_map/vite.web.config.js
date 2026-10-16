import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

const projectRoot = fileURLToPath(new URL('../../../../', import.meta.url));

export default defineConfig({
  root: fileURLToPath(new URL('./web', import.meta.url)),
  base: './',
  plugins: [{
    name: 'remove-qt-webchannel-from-browser-build',
    transformIndexHtml(html) {
      return html.replace('<script src="qrc:///qtwebchannel/qwebchannel.js"></script>', '');
    },
  }],
  build: {
    outDir: resolve(projectRoot, 'Web_Arayuzu/web/field-vector-map-dist'),
    emptyOutDir: true,
    target: 'es2022',
  },
});
