import test from 'node:test';
import assert from 'node:assert/strict';
import {beibeiGazeFrame,beibeiSpritePosition} from '../src/beibei-gaze.ts';
test('global cursor maps to all nine Beibei head directions',()=>{
 for(const [x,y,expected] of [[-100,-100,0],[0,-100,1],[100,-100,2],[-100,0,3],[0,0,4],[100,0,5],[-100,100,6],[0,100,7],[100,100,8]])assert.equal(beibeiGazeFrame(x,y),expected);
 assert.equal(beibeiGazeFrame(30,20,0),4);
});
test('hysteresis prevents head flicker around direction boundaries',()=>{
 const angle=Math.PI/8+.05;
 assert.equal(beibeiGazeFrame(Math.cos(angle)*200,Math.sin(angle)*200,5),5);
 assert.equal(beibeiGazeFrame(Math.cos(angle+.2)*200,Math.sin(angle+.2)*200,5),8);
});
test('atlas frame coordinates include last row and column',()=>{
 assert.equal(beibeiSpritePosition(0),'0% 0%');assert.equal(beibeiSpritePosition(15),'100% 100%');
});
