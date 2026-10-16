import * as THREE from 'three';

export function buildCampusArchitecture(scene:THREE.Scene,buildings:any[]){
 const clickable:THREE.Mesh[]=[],buildingMeshes=new Map<string,THREE.Mesh[]>();
 const material=(color:string)=>new THREE.MeshStandardMaterial({color,roughness:.86});
 const add=(geometry:THREE.BufferGeometry,color:string,parent:THREE.Object3D,b?:any)=>{
  const mesh=new THREE.Mesh(geometry,material(color));mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);
  if(b){mesh.userData.building=b.id;mesh.userData.baseColor=color;clickable.push(mesh);buildingMeshes.get(b.id)!.push(mesh)}
  return mesh;
 };
 const box=(w:number,h:number,d:number,color:string,x:number,y:number,z:number,parent:THREE.Object3D,b?:any)=>{const m=add(new THREE.BoxGeometry(w,h,d),color,parent,b);m.position.set(x,y,z);return m};
 const rounded=(w:number,d:number,r:number)=>{const s=new THREE.Shape(),x=-w/2,y=-d/2;s.moveTo(x+r,y);s.lineTo(x+w-r,y);s.quadraticCurveTo(x+w,y,x+w,y+r);s.lineTo(x+w,y+d-r);s.quadraticCurveTo(x+w,y+d,x+w-r,y+d);s.lineTo(x+r,y+d);s.quadraticCurveTo(x,y+d,x,y+d-r);s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);return s};
 const volume=(shape:THREE.Shape,height:number,color:string,x:number,y:number,z:number,parent:THREE.Object3D,b?:any)=>{const m=add(new THREE.ExtrudeGeometry(shape,{depth:height,bevelEnabled:false,curveSegments:20}),color,parent,b);m.rotation.x=-Math.PI/2;m.position.set(x,y,z);return m};
 const grid=(parent:THREE.Object3D,b:any,w:number,h:number,d:number,rows:number,cols:number,color='#778b91',yBase=0)=>{
  for(const axis of ['front','right','back']){
   const span=axis==='right'?d:w,ncols=axis==='right'?Math.max(2,Math.round(d/4)):cols;
   const paneW=span/ncols*.48,paneH=h/rows*.48;
   const windows=new THREE.InstancedMesh(new THREE.PlaneGeometry(paneW,paneH),material(color),rows*ncols);
   const matrix=new THREE.Matrix4();let i=0;
   for(let row=0;row<rows;row++)for(let col=0;col<ncols;col++){
    const offset=(col+.5)/ncols*span-span/2,y=yBase+(row+.5)/rows*h;
    if(axis==='right')matrix.makeRotationY(Math.PI/2).setPosition(w/2+.08,y,offset);
    else if(axis==='back')matrix.makeRotationY(Math.PI).setPosition(offset,y,-d/2-.08);
    else matrix.identity().setPosition(offset,y,d/2+.08);
    windows.setMatrixAt(i++,matrix);
   }
   windows.userData.building=b.id;parent.add(windows);clickable.push(windows);
  }
 };
 const archHole=(shape:THREE.Shape,cx:number,radius:number,spring:number,bottom:number)=>{const h=new THREE.Path();h.moveTo(cx-radius,bottom);h.lineTo(cx-radius,spring);h.absarc(cx,spring,radius,Math.PI,0,true);h.lineTo(cx+radius,bottom);h.closePath();shape.holes.push(h)};
 const stairs=(parent:THREE.Object3D,width:number,z:number,steps=5)=>{for(let i=0;i<steps;i++)box(width,.35*(i+1),1.5,'#d4d9d8',0,.175*(i+1),z+(steps-i)*1.5,parent)};

 for(const b of buildings){
  if(b.shape==='waypoint')continue;
  buildingMeshes.set(b.id,[]);const group=new THREE.Group();group.position.set(b.x,0,b.z);scene.add(group);
  const w=b.width,d=b.depth,h=b.height||b.floors*5;
  if(b.shape==='teaching'){
   box(w,h,d,'#f9faf5',0,h/2,0,group,b);box(w+.8,.8,d+.8,'#e0e3da',0,h+.4,0,group,b);
   grid(group,b,w,h,d,4,2,'#789093');
  }else if(b.shape==='information'){
   // Main block with a tall arched portal recessed into the front facade.
   const main=new THREE.Group();main.position.z=-4;group.add(main);box(w,h,d-8,'#f8faf5',0,h/2,0,main,b);grid(main,b,w,h,d-8,6,9,'#839aa6');
   const facade=new THREE.Shape();facade.moveTo(-w/2,0);facade.lineTo(w/2,0);facade.lineTo(w/2,h);facade.lineTo(-w/2,h);facade.closePath();archHole(facade,5,10,16,2);
   const portal=add(new THREE.ExtrudeGeometry(facade,{depth:4,bevelEnabled:false,curveSegments:28}),'#fffef8',group,b);portal.position.z=d/2-4;
   box(20,23,.4,'#53647e',5,13,d/2-5,group);
   const stairGroup=new THREE.Group();stairGroup.position.x=5;group.add(stairGroup);stairs(stairGroup,21,d/2-1,6);
   box(.35,20,.35,'#6e7884',8,12,d/2+8,group);box(7,4,.2,'#c64245',11.5,20,d/2+8,group);
   box(w+1,.8,d+1,'#bcc6c8',0,h+.4,0,group,b);
  }else if(b.shape==='library'){
   // Two connected rounded volumes create the S-shaped silhouette in the reference.
   for(const [x,z,width,depth,height,r] of [[-8,10,29,23,h-4,6],[7,-10,29,23,h+2,4]]){
    const shape=rounded(width,depth,r);volume(shape,height,'#cbb99c',x,0,z,group,b);volume(shape,.7,'#818a79',x,height,z,group,b);
    for(let y=4;y<height;y+=5)volume(shape,.48,'#f5f2e4',x,y,z,group);
    for(let k=0;k<5;k++)box(.55,height-2,.5,'#eae6d6',x-width/2+6+k*4, height/2,z+depth/2+.1,group);
   }
   box(10,h-7,9,'#ccbb9d',0,(h-7)/2,0,group,b);
  }else if(b.shape==='gym'){
   box(w,h,d,'#eee9d4',0,h/2,0,group,b);box(w+3,1.8,d+3,'#b6c5d1',0,h+.9,0,group,b);
   // Reference gym has a low roof, ochre fins, and a circular feature on the facade.
   for(let x=-w/2+6;x<w/2;x+=9){box(1.5,h-3,1,'#d2bf91',x,h/2,d/2+.5,group);if(Math.abs(x)>9)for(let y=5;y<h-2;y+=6)box(5,4,.35,'#697d86',x+3,y,d/2+.1,group)}
   const circle=add(new THREE.CircleGeometry(7,36),'#667d86',group);circle.position.set(2,14,d/2+.65);
   const ring=add(new THREE.TorusGeometry(7.3,.8,6,40),'#f9f8ed',group);ring.position.set(2,14,d/2+.8);
   box(1,13,.5,'#f9f8ed',2,14,d/2+1,group);box(13,1,.5,'#f9f8ed',2,14,d/2+1,group);
  }else if(b.shape==='gate'){
   for(const x of [-w/2+2,w/2-2])box(2,8,2,'#5b614c',x,4,0,group,b);
   box(w,3,2,'#484a3e',0,8,0,group,b);box(w-4,.25,.3,'#c5b474',0,8,1.2,group);
  }else if(b.type==='academic'){
   box(w,h,d,'#d9d8c9',0,h/2,0,group,b);grid(group,b,w,h,d,5,6,'#727d7b');
   box(w+1,.6,d+1,'#b6bdaf',0,h+.3,0,group,b);
   const upper=new THREE.Group();upper.position.set(-2,h,-2);group.add(upper);box(w*.7,5,d*.6,'#e8e8dc',0,2.5,0,upper,b);grid(upper,b,w*.7,5,d*.6,1,4,'#7b8482');box(w*.72,.6,d*.64,'#bdc4b4',0,5.3,0,upper);
  }else if(b.type==='dining'){
   box(w,h,d,'#dbdfd4',0,h/2,0,group,b);box(w+1,.9,d+1,'#9ead9e',0,h+.45,0,group,b);grid(group,b,w,h,d,3,7,'#76918b');
   for(let y=4;y<h;y+=5)box(w,.45,.35,'#e5e9df',0,y,d/2+.2,group);
  }else if(b.type==='culture'){
   box(w,h*.7,d,'#f1f1e6',0,h*.35,0,group,b);box(w+3,1,d+2,'#d3d8c9',0,h*.7+.5,0,group,b);grid(group,b,w,h*.7,d,2,4,'#6f7f7b');
  }else{
   const color=b.id==='LIUDE'?'#e0dbca':'#e6e8dd';box(w,h,d,color,0,h/2,0,group,b);grid(group,b,w,h,d,b.floors,5,'#758581');box(w+1,.8,d+1,'#b7c2b3',0,h+.4,0,group,b);
  }
 }

 const wings=buildings.filter(b=>b.shape==='teaching').sort((a,b)=>a.x-b.x);
 if(wings.length===4){
  const left=wings[0].x-wings[0].width/2,right=wings[3].x+wings[3].width/2,height=27,front=wings[0].z+wings[0].depth/2,rear=wings[0].z-wings[0].depth/2;
  const arcadeShape=new THREE.Shape();arcadeShape.moveTo(left,0);arcadeShape.lineTo(right,0);arcadeShape.lineTo(right,height);arcadeShape.lineTo(left,height);arcadeShape.closePath();
  const archCenters=wings.slice(1).map((b,i)=>(b.x+wings[i].x)/2);
  for(const x of archCenters)archHole(arcadeShape,x,10.5,12,1.8);
  const arcade=add(new THREE.ExtrudeGeometry(arcadeShape,{depth:5,bevelEnabled:false,curveSegments:32}),'#f7faf4',scene);arcade.position.z=front-5;arcade.userData.teachingFacade=true;clickable.push(arcade);
  box(right-left+.8,.8,5.8,'#e4e6da',(left+right)/2,height+.4,front-2.5,scene);
  box(right-left,height,4,'#f5f6ec',(left+right)/2,height/2,rear,scene);
  box(right-left+.8,.8,4.8,'#e2e5d8',(left+right)/2,height+.4,rear,scene);
  for(const x of archCenters){
   const steps=new THREE.Group();steps.position.x=x;scene.add(steps);stairs(steps,21,front,5);
   box(21,.18,37,'#b2c5a4',x,.15,wings[0].z,scene);box(16,.2,31,'#dde4d6',x,.3,wings[0].z,scene);
   for(let j=0;j<3;j++)box(2,2.8,1,'#91a1a1',x-4+j*4,24,front+.05,scene);
  }
 }
 return {clickable,buildingMeshes};
}
