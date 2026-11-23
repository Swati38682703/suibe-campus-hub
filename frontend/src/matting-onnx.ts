/**
 * 本地 ONNX 抠图（u2netp，自托管开源模型，免费离线）。
 * 预处理/后处理规格对齐 rembg U2netpSession：
 *  - 输入 RGB，拉伸缩放到 320×320
 *  - 按整图最大值归一化，再减 ImageNet 均值、除标准差
 *  - 张量 [1,3,320,320]，模型输入名 input.1，取第 0 个输出主蒙版
 *  - min-max 归一化蒙版，放大回原图分辨率，写入 alpha 通道
 * 模型：/models/u2netp.onnx（4,574,861 字节，md5 8e83ca70e441ab06c318d82300c84806）
 * 运行时 wasm：/wasm/（onnxruntime-web 本地拷贝）
 */
import type {InferenceSession, Tensor} from 'onnxruntime-web';

const MODEL_URL = '/models/u2netp.onnx';
const SIZE = 320;
const MEAN = [0.485, 0.456, 0.406];
const STD = [0.229, 0.224, 0.225];

type OrtModule = typeof import('onnxruntime-web/wasm');
let ortModule: OrtModule | null = null;
let sessionPromise: Promise<InferenceSession> | null = null;

async function loadOrt(): Promise<OrtModule> {
  if (!ortModule) ortModule = await import('onnxruntime-web/wasm');
  return ortModule;
}

function getSession(): Promise<InferenceSession> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      const ort = await loadOrt();
      ort.env.wasm.wasmPaths = '/wasm/';
      // 有 SharedArrayBuffer（跨域隔离）时才开多线程，否则退回单线程
      ort.env.wasm.numThreads = (typeof SharedArrayBuffer !== 'undefined')
        ? Math.min(4, navigator.hardwareConcurrency || 2)
        : 1;
      const res = await fetch(MODEL_URL);
      if (!res.ok) throw new Error(`模型加载失败：HTTP ${res.status}`);
      const buf = await res.arrayBuffer();
      return ort.InferenceSession.create(buf, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all',
      });
    })();
    sessionPromise.catch(() => {
      // 失败后允许下次重新尝试
      sessionPromise = null;
    });
  }
  return sessionPromise;
}

/**
 * 空闲预热：页面打开后在后台静默加载模型并编译会话，
 * 这样第一张照片上传时不再等待 4.5MB 模型拉取与 wasm 编译。
 * 预热失败不报错，首次真正抠图时会重试。
 */
export function warmupMatting(): void {
  const idle: any = (window as any).requestIdleCallback;
  const run = () => { void getSession().catch(() => { /* 下次重试 */ }); };
  if (typeof idle === 'function') idle(run, {timeout: 2500});
  else setTimeout(run, 600);
}

/**
 * 对照片做本地模型抠图，返回透明背景 PNG dataURL；
 * 任一步失败返回 null，由上层走本地洪水填充或原图兜底。
 */
export async function cutoutWithOnnx(file: Blob): Promise<string | null> {
  const bitmap = await createImageBitmap(file);
  try {
    const sw = bitmap.width;
    const sh = bitmap.height;
    const session = await getSession();

    // 1) 缩放到 320×320（rembg 直接拉伸，不做 letterbox）
    const small = document.createElement('canvas');
    small.width = SIZE;
    small.height = SIZE;
    const sctx = small.getContext('2d', {willReadFrequently: true});
    if (!sctx) return null;
    sctx.drawImage(bitmap, 0, 0, SIZE, SIZE);
    const smallData = sctx.getImageData(0, 0, SIZE, SIZE).data;

    // 2) 按整图最大值归一化 → 减均值除标准差 → NCHW
    let maxV = 1e-6;
    for (let i = 0; i < smallData.length; i += 4) {
      if (smallData[i] > maxV) maxV = smallData[i];
      if (smallData[i + 1] > maxV) maxV = smallData[i + 1];
      if (smallData[i + 2] > maxV) maxV = smallData[i + 2];
    }
    const plane = SIZE * SIZE;
    const tensor = new Float32Array(3 * plane);
    for (let p = 0; p < plane; p++) {
      const r = smallData[p * 4] / maxV;
      const g = smallData[p * 4 + 1] / maxV;
      const b = smallData[p * 4 + 2] / maxV;
      tensor[p] = (r - MEAN[0]) / STD[0];
      tensor[plane + p] = (g - MEAN[1]) / STD[1];
      tensor[2 * plane + p] = (b - MEAN[2]) / STD[2];
    }

    // 3) 推理，取主输出
    const ort = await loadOrt();
    const feeds: Record<string, Tensor> = {
      [session.inputNames[0]]: new ort.Tensor('float32', tensor, [1, 3, SIZE, SIZE]),
    };
    const out = await session.run(feeds);
    const pred = out[session.outputNames[0]].data as Float32Array;

    // 4) min-max 归一化到 0..255 的 L 蒙版（320×320）
    let mn = Infinity;
    let mx = -Infinity;
    for (let i = 0; i < pred.length; i++) {
      if (pred[i] < mn) mn = pred[i];
      if (pred[i] > mx) mx = pred[i];
    }
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = SIZE;
    maskCanvas.height = SIZE;
    const mctx = maskCanvas.getContext('2d', {willReadFrequently: true});
    if (!mctx) return null;
    const maskImg = mctx.createImageData(SIZE, SIZE);
    const span = mx - mn || 1;
    for (let i = 0; i < pred.length; i++) {
      const v = Math.round(((pred[i] - mn) / span) * 255);
      maskImg.data[i * 4] = v;
      maskImg.data[i * 4 + 1] = v;
      maskImg.data[i * 4 + 2] = v;
      maskImg.data[i * 4 + 3] = 255;
    }
    mctx.putImageData(maskImg, 0, 0);

    // 5) 蒙版映射回原图分辨率
    const maskFull = document.createElement('canvas');
    maskFull.width = sw;
    maskFull.height = sh;
    const mfctx = maskFull.getContext('2d', {willReadFrequently: true});
    if (!mfctx) return null;
    mfctx.imageSmoothingEnabled = true;
    mfctx.imageSmoothingQuality = 'high';
    mfctx.drawImage(maskCanvas, 0, 0, sw, sh);
    const maskPixels = mfctx.getImageData(0, 0, sw, sh).data;

    // 6) 边缘连通背景清理：从四周边界 BFS，抹除与边界连通的低透明度残留
    //    （模型常把桌面/毛毡背景连同主体保留成半透明块，不清理会被垫边放大成大片白）
    const bg = new Uint8Array(sw * sh);
    const stack: number[] = [];
    for (let x = 0; x < sw; x++) { stack.push(x); stack.push((sh - 1) * sw + x); }
    for (let y = 0; y < sh; y++) { stack.push(y * sw); stack.push(y * sw + sw - 1); }
    while (stack.length) {
      const p = stack.pop()!;
      if (bg[p]) continue;
      if (maskPixels[p * 4] >= 128) continue;
      bg[p] = 1;
      const x = p % sw, y = (p / sw) | 0;
      if (x > 0) stack.push(p - 1);
      if (x < sw - 1) stack.push(p + 1);
      if (y > 0) stack.push(p - sw);
      if (y < sh - 1) stack.push(p + sw);
    }

    // 7) 合成 RGBA：alpha 取蒙版；低 alpha 直接清零，去掉边缘浅色残影
    const outCanvas = document.createElement('canvas');
    outCanvas.width = sw;
    outCanvas.height = sh;
    const octx = outCanvas.getContext('2d', {willReadFrequently: true});
    if (!octx) return null;
    octx.drawImage(bitmap, 0, 0, sw, sh);
    const outData = octx.getImageData(0, 0, sw, sh);
    let transparent = 0;
    for (let p = 0; p < sw * sh; p++) {
      const i = p * 4;
      const m = maskPixels[i];
      let a: number;
      if (bg[p]) a = 0;
      else a = m < 40 ? 0 : m < 128 ? Math.round(((m - 40) / 88) * 255) : m;
      outData.data[i + 3] = a;
      if (a === 0) transparent++;
    }
    // 透明占比过低（背景没抠掉）或过高（主体被误删）都判定失败，回退兜底
    const ratio = transparent / (sw * sh);
    if (ratio < 0.06 || ratio > 0.92) return null;
    octx.putImageData(outData, 0, 0);
    return outCanvas.toDataURL('image/png');
  } catch {
    return null;
  } finally {
    bitmap.close();
  }
}
