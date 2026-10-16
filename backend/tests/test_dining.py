import re

def payload(client, email='food@example.com'):
    captcha=client.get('/api/captcha').json()
    return dict(nickname='食客同学',email=email,overall=4,dimensions=[4,5,3,4],text='口味不错，分量也合适。',captcha_id=captcha['id'],captcha_answer=''.join(re.findall(r'<text[^>]*>([^<])</text>',captcha['svg'])))

def test_dining_review_lifecycle(client):
    rows=client.get('/api/dining').json()
    assert len(rows)==12 and all(d['demo'] for d in rows)
    result=client.post('/api/dining/d01/reviews',json=payload(client))
    assert result.status_code==201
    value=result.json(); rid=value['id']
    dish=lambda: next(d for d in client.get('/api/dining').json() if d['id']=='d01')
    assert dish()['count']==0
    assert client.put('/api/admin/reviews/'+rid,json={'status':'normal'}).status_code==403
    headers={'X-Admin-Token':'test-admin-only'}
    assert client.put('/api/admin/reviews/'+rid,json={'status':'normal'},headers=headers).status_code==200
    assert dish()['average']==4 and dish()['count']==1
    assert not {'identity_hash','token_hash','email','management_token'} & dish()['reviews'][0].keys()
    assert client.post('/api/dining/d01/reviews',json=payload(client)).status_code==409
    assert client.delete('/api/reviews/'+rid).status_code==403
    assert client.put('/api/admin/reviews/'+rid,json={'status':'hidden'},headers=headers).status_code==200
    assert dish()['count']==0
    assert client.delete('/api/reviews/'+rid,headers={'X-Review-Token':value['management_token']}).status_code==200
    assert dish()['count']==0

def test_invalid_dining_reviews(client):
    assert client.post('/api/dining/missing/reviews',json=payload(client,'missing@example.com')).status_code==404
    body=payload(client,'invalid@example.com');body['overall']=6
    assert client.post('/api/dining/d02/reviews',json=body).status_code==422
    body=payload(client,'captcha@example.com');body['captcha_answer']='WRONG'
    assert client.post('/api/dining/d02/reviews',json=body).status_code==400
