import {cutoutWithOnnx} from './matting-onnx';

export type PhotoFrame = 'dashed' | 'solid' | 'none';

export interface Stamp {id: string; photo: string; date: string; frame?: PhotoFrame}
function database(): Promise<IDBDatabase> {
  return new Promise((resolve,reject)=>{
    // 沿用历史版本号 2：旧库可能已建 diary 表，这里只确保 stamps 表存在，不降级版本
    const request=indexedDB.open('suibe-food-passport',2);
    request.onupgradeneeded=()=>{
      if(!request.result.objectStoreNames.contains('stamps'))request.result.createObjectStore('stamps',{keyPath:'id'});
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(new Error('无法打开照片存储，请检查浏览器存储权限'));
  });
}
export async function stamps(): Promise<Stamp[]> {
  const db=await database();
  try {return await new Promise((resolve,reject)=>{
    const tx=db.transaction('stamps','readonly'),request=tx.objectStore('stamps').getAll();
    tx.oncomplete=()=>resolve(request.result);tx.onerror=()=>reject(new Error('读取集邮失败'));
  });} finally {db.close();}
}
export async function saveStamp(value: Stamp | string): Promise<void> {
  const db=await database();
  try {await new Promise<void>((resolve,reject)=>{
    const tx=db.transaction('stamps','readwrite'),store=tx.objectStore('stamps');
    if(typeof value==='string')store.delete(value);else store.put(value);
    tx.oncomplete=()=>resolve();tx.onerror=()=>reject(new Error('保存失败，浏览器存储空间可能不足'));
    tx.onabort=()=>reject(new Error('保存已中止，请重试'));
  });} finally {db.close();}
}

function downscale(bitmap: ImageBitmap, transparent: boolean): string {
  const ratio=Math.min(1,960/Math.max(bitmap.width,bitmap.height));
  const canvas=document.createElement('canvas');
  canvas.width=Math.round(bitmap.width*ratio);canvas.height=Math.round(bitmap.height*ratio);
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('浏览器暂不支持图片处理');
  ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
  return transparent?canvas.toDataURL('image/png'):canvas.toDataURL('image/jpeg',0.82);
}

/**
 * 本地兜底抠图：从图片四周边界做洪水填充，把与边角背景颜色相近且连通的区域抹成透明。
 * 仅适用于背景较纯净（白桌、浅色墙面等）的照片；背景杂乱时返回 null，保留原图。
 */
function localMatting(file: Blob): Promise<string | null> {
  return new Promise(async resolve=>{
    let bitmap: ImageBitmap|null=null;
    try {
      bitmap=await createImageBitmap(file);
      const w=bitmap.width,h=bitmap.height;
      const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
      const ctx=canvas.getContext('2d',{willReadFrequently:true});
      if(!ctx){resolve(null);return}
      ctx.drawImage(bitmap,0,0,w,h);bitmap.close();bitmap=null;
      const img=ctx.getImageData(0,0,w,h);const data=img.data;
      const corners=[0,w-1,(h-1)*w,w*h-1].map(p=>p*4);
      const ref=[0,1,2].map(c=>Math.round(corners.reduce((s,i)=>s+data[i+c],0)/4));
      const tol=40;
      const similar=(i:number)=>Math.abs(data[i]-ref[0])<=tol&&Math.abs(data[i+1]-ref[1])<=tol&&Math.abs(data[i+2]-ref[2])<=tol;
      const visited=new Uint8Array(w*h);
      const stack:number[]=[];
      for(let x=0;x<w;x++){stack.push(x);stack.push((h-1)*w+x)}
      for(let y=0;y<h;y++){stack.push(y*w);stack.push(y*w+w-1)}
      while(stack.length){
        const p=stack.pop()!;if(visited[p])continue;visited[p]=1;
        const i=p*4;if(!similar(i))continue;
        data[i+3]=0;
        const x=p%w,y=(p/w)|0;
        if(x>0)stack.push(p-1);if(x<w-1)stack.push(p+1);
        if(y>0)stack.push(p-w);if(y<h-1)stack.push(p+w);
      }
      let transparent=0;
      for(let p=0;p<w*h;p++)if(data[p*4+3]===0)transparent++;
      // 透明占比过低说明背景不纯净，过高说明误删主体；都放弃抠图
      if(transparent<w*h*0.06||transparent>w*h*0.92){resolve(null);return}
      ctx.putImageData(img,0,0);
      resolve(canvas.toDataURL('image/png'));
    } catch {
      resolve(null);
    } finally {
      bitmap?.close();
    }
  });
}

/**
 * 处理打卡照片（全程本地、免费、无外部 API 调用）：
 * 1. 优先浏览器端本地 ONNX 模型（u2netp，自托管 wasm/模型）分割，输出透明 PNG；
 * 2. 模型不可用或效果异常时走本地洪水填充抠图；
 * 3. 都失败则回退原始压缩 JPEG，不阻断上传。
 */
export async function photoData(file: File): Promise<string> {
  if(!file.type.startsWith('image/')||file.size>20*1024*1024)throw new Error('请选择 20MB 以内的图片');
  let source: Blob = file;
  let transparent = false;
  const onnx = await cutoutWithOnnx(file);
  if(onnx){
    const resp=await fetch(onnx);
    source=await resp.blob();transparent=true;
  }
  if(!transparent){
    const local = await localMatting(file);
    if(local){
      const resp=await fetch(local);
      source=await resp.blob();transparent=true;
    }
  }
  const bitmap=await createImageBitmap(source);
  try {
    return downscale(bitmap,transparent);
  } finally {bitmap.close();}
}
