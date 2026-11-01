import test from 'node:test';
import assert from 'node:assert/strict';
import {beibeiThemeForPath,beibeiImage,beibeiThemes} from '../src/beibei-themes.ts';

test('Beibei selects the approved outfit for each page and its detail routes',()=>{
 for(const id of Object.keys(beibeiThemes).filter(id=>id!=='campus')){
  assert.equal(beibeiThemeForPath('/'+id),id);
  assert.equal(beibeiThemeForPath('/'+id+'/detail'),id);
  assert.equal(beibeiImage(id),'/assets/beibei/'+id+'.webp');
 }
});
test('shared assistant, search and admin use campus Beibei without matching similar paths',()=>{
 for(const path of ['/','/assistant','/search','/admin','/rooms-other','/toString','/constructor'])assert.equal(beibeiThemeForPath(path),'campus');
 assert.equal(beibeiImage('campus'),'/assets/beibei/campus.webp');
});
