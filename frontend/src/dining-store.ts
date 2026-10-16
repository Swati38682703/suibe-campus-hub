export interface Stamp {id: string; photo: string; date: string}
function database(): Promise<IDBDatabase> {
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('suibe-food-passport',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('stamps',{keyPath:'id'});
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
    tx.oncomplete=()=>resolve();tx.onerror=()=>reject(new Error('保存失败，浏览器存储空间可能不足'));tx.onabort=()=>reject(new Error('保存已中止，请重试'));
  });} finally {db.close();}
}
export async function photoData(file: File): Promise<string> {
  if(!file.type.startsWith('image/')||file.size>20*1024*1024)throw new Error('请选择 20MB 以内的图片');
  const bitmap=await createImageBitmap(file);
  try {
    const ratio=Math.min(1,960/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*ratio);canvas.height=Math.round(bitmap.height*ratio);
    const ctx=canvas.getContext('2d');if(!ctx)throw new Error('浏览器暂不支持图片处理');
    ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);return canvas.toDataURL('image/jpeg',0.82);
  } finally {bitmap.close();}
}
