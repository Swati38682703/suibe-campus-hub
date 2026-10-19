"""HiAgent Agent API adapter; campus tools continue to execute in this backend."""
import json
import os
from uuid import uuid4
import httpx


class HiAgentError(Exception):
    pass


def configured():
    return bool(os.getenv('HIAGENT_API_KEY'))



def load_json(answer):
    try:
        return json.loads(answer)
    except json.JSONDecodeError:
        # Qwen occasionally omits a closing brace. Repair only missing container
        # terminators; never alter strings, field names, values, or tool arguments.
        stack = []
        output = []
        quoted = escaped = False
        pairs = {'{': '}', '[': ']'}
        for char in answer:
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in pairs:
                stack.append(char)
            elif char in '}]':
                opener = '{' if char == '}' else '['
                if opener not in stack:
                    raise ValueError('Unmatched JSON terminator')
                while stack[-1] != opener:
                    output.append(pairs[stack.pop()])
                stack.pop()
            output.append(char)
        if quoted:
            raise ValueError('Unterminated JSON string')
        output.extend(pairs[char] for char in reversed(stack))
        return json.loads(''.join(output))


def parse_message(answer, tools):
    if not isinstance(answer, str):
        raise HiAgentError('学校智能体未返回有效回答。')
    answer = answer.strip()
    if answer.startswith('```') and answer.endswith('```'):
        answer = answer.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        message = load_json(answer)
        if not isinstance(message, dict):
            raise ValueError()
        calls = message.get('tool_calls', [])
        if not isinstance(calls, list) or len(calls) > 4:
            raise ValueError()
        names = {t['function']['name'] for t in tools}
        normalized = []
        for i, call in enumerate(calls):
            function = call['function']
            if function['name'] not in names:
                raise ValueError()
            args = function['arguments']
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(args, dict):
                raise ValueError()
            # Send the complete calendar so combined topics cannot hide exam or holiday facts.
            if function['name'] == 'get_calendar':
                args.pop('topic', None)
            normalized.append(dict(id='hia-'+str(i), type='function', function=dict(
                name=function['name'], arguments=json.dumps(args, ensure_ascii=False))))
        content = message.get('content')
        if content is not None and not isinstance(content, str):
            raise ValueError()
        if not normalized and not (content and content.strip()):
            raise ValueError()
        return dict(role='assistant', content=content, tool_calls=normalized)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        raise HiAgentError('学校智能体返回格式不符合工具协议，请稍后重试或联系维护者。') from None


async def completion(client, messages, tools):
    base = os.getenv('HIAGENT_BASE_URL', 'https://agent.suibe.edu.cn/api/proxy/api/v1').rstrip('/')
    headers = {'Apikey': os.environ['HIAGENT_API_KEY'], 'Content-Type': 'application/json'}
    # Each request contains its own bounded history; no cross-user platform conversation reuse.
    user = uuid4().hex[:20]
    created = await client.post(base+'/create_conversation', headers=headers, json={'UserID': user})
    created.raise_for_status()
    try:
        conversation = created.json()['Conversation']['AppConversationID']
        if not isinstance(conversation, str) or not conversation:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise HiAgentError('学校智能体创建会话失败，请检查发布状态和 API 权限。') from None
    query = json.dumps(dict(messages=messages, tools=tools), ensure_ascii=False)
    for attempt in range(2):
        response = await client.post(base+'/chat_query_v2', headers=headers, json={
            'UserID': user, 'AppConversationID': conversation, 'ResponseMode': 'blocking',
            'Query': query})
        response.raise_for_status()
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            if data.get('event') in ('error', 'message_failed'):
                raise HiAgentError('学校智能体执行失败，请检查模型服务或调用限额。')
        except ValueError:
            raise HiAgentError('学校智能体返回了无法解析的数据。') from None
        try:
            message = parse_message(data.get('answer'), tools)
            break
        except HiAgentError:
            if attempt:
                raise
            query += '\n上次输出格式校验失败。请重新处理上面的请求，只返回合法 JSON；arguments 必须是对象。不要添加代码块或说明文字。'
    return httpx.Response(200, json={'choices': [{'message': message}]},
                          request=httpx.Request('POST', base+'/chat_query_v2'))
