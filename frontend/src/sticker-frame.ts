/**
 * 贴纸轮廓边合成（沿抠图主体的 alpha 蒙版描边，不套矩形边框）：
 *  - solid：沿轮廓向外膨胀一圈较厚的白色模切垫边，外缘羽化（Nosh 式贴纸）
 *  - dashed：仅在主体外圈轮廓环上按块留暖棕色虚线描边
 *  - none：原样返回透明抠图
 * 输入为透明 PNG dataURL；若图片无透明背景（兜底 JPEG），直接原样返回。
 */
import type {PhotoFrame} from './dining-store';

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve,reject)=>{
    const img=new Image();
    img.onload=()=>resolve(img);
    img.onerror=()=>reject(new Error('预览图读取失败'));
    img.src=src;
  });
}

/** 对 0/255 前景掩码做 k 次 3×3 膨胀（向外扩一圈） */
function dilate(mask: Uint8Array, w: number, h: number, k: number): Uint8Array {
  let cur=mask.slice();
  for(let it=0; it<k; it++){
    const next=cur.slice();
    for(let y=0;y<h;y++){
      for(let x=0;x<w;x++){
        const p=y*w+x;
        if(cur[p]>0) continue;
        let near=false;
        for(let dy=-1;dy<=1&&!near;dy++){
          for(let dx=-1;dx<=1;dx++){
            const nx=x+dx, ny=y+dy;
            if(nx<0||ny<0||nx>=w||ny>=h) continue;
            if(cur[ny*w+nx]>0){near=true;break}
          }
        }
        if(near) next[p]=255;
      }
    }
    cur=next;
  }
  return cur;
}

export async function bakeSticker(raw: string, frame: PhotoFrame): Promise<string> {
  const img=await loadImage(raw);
  const w=img.naturalWidth, h=img.naturalHeight;
  if(!w||!h) return raw;

  const base=document.createElement('canvas');
  base.width=w; base.height=h;
  const bctx=base.getContext('2d',{willReadFrequently:true});
  if(!bctx) return raw;
  bctx.drawImage(img,0,0,w,h);
  const src=bctx.getImageData(0,0,w,h);
  const data=src.data;

  const alpha=new Uint8Array(w*h);
  let transparent=0;
  for(let p=0;p<w*h;p++){
    const a=data[p*4+3];
    alpha[p]=a;
    if(a===0) transparent++;
  }
  // 无透明区域（兜底原图）或无边框档：不做轮廓处理
  if(transparent/(w*h)<0.06||frame==='none') return raw;

  const pad=Math.max(10,Math.round(Math.min(w,h)*0.02));
  // 膨胀基底只取较实的主体像素，避免半透明残影被填成大片白色
  const solidMask=alpha.map(v=>v>=64?255:0);
  const dil=dilate(solidMask,w,h,pad);

  const W=w+pad*2, H=h+pad*2;
  const out=document.createElement('canvas');
  out.width=W; out.height=H;
  const octx=out.getContext('2d',{willReadFrequently:true});
  if(!octx) return raw;

  if(frame==='solid'){
    // 蒙版画到垫边画布，羽化外缘后取其 alpha 填白
    const maskCanvas=document.createElement('canvas');
    maskCanvas.width=w; maskCanvas.height=h;
    const mctx=maskCanvas.getContext('2d',{willReadFrequently:true});
    if(!mctx) return raw;
    const mImg=mctx.createImageData(w,h);
    for(let p=0;p<w*h;p++){
      const v=dil[p];
      mImg.data[p*4]=255; mImg.data[p*4+1]=255; mImg.data[p*4+2]=255; mImg.data[p*4+3]=v;
    }
    mctx.putImageData(mImg,0,0);

    const padCanvas=document.createElement('canvas');
    padCanvas.width=W; padCanvas.height=H;
    const pctx=padCanvas.getContext('2d')!;
    pctx.filter='blur(2px)';
    pctx.drawImage(maskCanvas,pad,pad);
    pctx.globalCompositeOperation='source-in';
    pctx.fillStyle='#ffffff';
    pctx.fillRect(0,0,W,H);

    octx.drawImage(padCanvas,0,0);
  }else{
    // dashed：仅在外圈轮廓环上按块留暖棕色虚线描边
    const layer=octx.createImageData(W,H);
    const ld=layer.data;
    const block=Math.max(6,Math.round(Math.min(w,h)/120));
    const DASH=[217,167,111];
    for(let y=0;y<h;y++){
      for(let x=0;x<w;x++){
        const p=y*w+x;
        if(dil[p]===0) continue;
        const ring=dil[p]>0&&alpha[p]<64;
        if(ring&&((x/block|0)+(y/block|0))%2===0){
          const o=(y+pad)*W+(x+pad);
          ld[o*4]=DASH[0]; ld[o*4+1]=DASH[1]; ld[o*4+2]=DASH[2]; ld[o*4+3]=255;
        }
      }
    }
    octx.putImageData(layer,0,0);
  }

  octx.drawImage(base,pad,pad);
  return out.toDataURL('image/png');
}
