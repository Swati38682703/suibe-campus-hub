export interface StickerTransform {x:number;y:number;scale:number;rotation:number}

function dataUrl(blob:Blob):Promise<string>{return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(new Error('无法读取抠图结果'));reader.readAsDataURL(blob)})}

export async function removeFoodBackground(file:File,onProgress:(value:number)=>void):Promise<string>{
  const {removeBackground}=await import('@imgly/background-removal');
  const progress=new Map<string,{current:number;total:number}>();
  const blob=await removeBackground(file,{model:'isnet_quint8',output:{format:'image/png',quality:1},progress:(key:string,current:number,total:number)=>{progress.set(key,{current,total});const values=[...progress.values()],done=values.reduce((sum,item)=>sum+item.current,0),all=values.reduce((sum,item)=>sum+item.total,0);onProgress(all?Math.min(95,Math.round(done/all*95)):10)}});
  onProgress(100);return dataUrl(blob);
}

export async function renderFoodSticker(source:string,transform:StickerTransform):Promise<string>{
  const image=new Image();image.src=source;await image.decode();
  const canvas=document.createElement('canvas');canvas.width=800;canvas.height=600;
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('浏览器暂不支持贴纸编辑');
  const fit=Math.min(620/image.naturalWidth,470/image.naturalHeight)*transform.scale;
  ctx.translate(400+transform.x*2,300+transform.y*2);ctx.rotate(transform.rotation*Math.PI/180);
  ctx.drawImage(image,-image.naturalWidth*fit/2,-image.naturalHeight*fit/2,image.naturalWidth*fit,image.naturalHeight*fit);
  return canvas.toDataURL('image/png');
}
