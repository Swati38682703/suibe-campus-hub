import {defineConfig,type Plugin} from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));

/**
 * ort-web 的胶水 mjs 是运行时动态 import 的，放在 public/ 下时，
 * Vite 开发服务器会把带查询参数的请求误送进源码转译中间件并报错。
 * 这里前置一个静态中间件，把 /wasm/ 下的文件按静态资源直接返回（忽略查询串）。
 * 生产构建走 public 拷贝，不经过该中间件。
 */
function serveWasmStatic(): Plugin {
  const dir = path.join(root, 'public', 'wasm');
  const mime: Record<string,string> = {
    '.mjs': 'text/javascript',
    '.wasm': 'application/wasm',
  };
  return {
    name: 'public-wasm-static',
    configureServer(server) {
      server.middlewares.use((req,res,next)=>{
        const url = (req.url || '').split('?')[0];
        if(!url.startsWith('/wasm/')) return next();
        const file = path.join(dir, decodeURIComponent(url.slice('/wasm/'.length)));
        if(!file.startsWith(dir) || !fs.existsSync(file) || !fs.statSync(file).isFile()) return next();
        res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
        res.setHeader('Cache-Control','no-cache');
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  plugins:[react(),serveWasmStatic()],
  server:{port:5173,proxy:{'/api':'http://127.0.0.1:8000'},headers:{
    // 多线程 wasm 需要 SharedArrayBuffer，必须跨域隔离
    'Cross-Origin-Opener-Policy':'same-origin',
    'Cross-Origin-Embedder-Policy':'require-corp'
  }},
  build:{rollupOptions:{output:{manualChunks:{react:['react','react-dom','react-router-dom']}}}}
});
