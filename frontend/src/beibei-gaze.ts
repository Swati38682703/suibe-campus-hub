// Direction sectors follow the interaction described by nilbuild/page-mascot (MIT).
export const beibeiExpressions={blink:9,wink:10,happy:11,surprised:12,thinking:13,sleepy:14,dizzy:15} as const;
export type BeibeiExpression=keyof typeof beibeiExpressions;
const clockwise=[5,8,7,6,3,0,1,2];
export function beibeiGazeFrame(dx:number,dy:number,previous=4){
 if(Math.hypot(dx,dy)<56)return 4;
 const angle=Math.atan2(dy,dx),sector=Math.PI/4;
 const last=clockwise.indexOf(previous);
 if(last!==-1){const delta=angle-last*sector;if(Math.abs(Math.atan2(Math.sin(delta),Math.cos(delta)))<sector/2+.12)return previous}
 return clockwise[(Math.round(angle/sector)+8)%8];
}
export function beibeiSpritePosition(frame:number){return `${frame%4*100/3}% ${Math.floor(frame/4)*100/3}%`}
