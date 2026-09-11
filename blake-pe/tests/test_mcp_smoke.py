import asyncio,json,os,tempfile,sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from fixtures import profile,PRIMARY
async def main():
    with tempfile.TemporaryDirectory() as directory:
        params=StdioServerParameters(command=str(ROOT/'server/run.sh'),cwd=str(ROOT),env={**os.environ,'BLAKE_PE_DATA_DIR':directory,'BLAKE_PE_PYTHON':sys.executable})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                init=await session.initialize();assert init.serverInfo.name=='Blake-PE'
                tools=(await session.list_tools()).tools;assert len(tools)==9
                def decode(result):
                    assert not result.isError,result
                    return result.structuredContent or json.loads(next(x.text for x in result.content if x.type=='text'))
                assert decode(await session.call_tool('list_senders',{}))['senders']==[]
                Path(directory,'accounts.json').write_text(json.dumps({'accounts':[profile()]}))
                assert decode(await session.call_tool('list_senders',{}))['senders'][0]['sender']==PRIMARY
                draft=decode(await session.call_tool('prepare_email',{'sender':PRIMARY,'recipients':['student@example.com'],'subject':'Test','body':'Draft only.'}))
                assert draft['from']==PRIMARY and draft['email_sent'] is False
                invalid=await session.call_tool('prepare_email',{'sender':'unknown@example.com','recipients':['student@example.com'],'subject':'Test','body':'Body'})
                assert invalid.isError
                for name in ('inbox_status','list_inbox','search_inbox','read_inbox_email'):
                    tool=next(x for x in tools if x.name==name)
                    assert 'account' in tool.inputSchema['required']
                    assert tool.annotations.readOnlyHint
                receipt=decode(await session.call_tool('get_delivery_status',{'draft_id':draft['draft_id']}))
                assert receipt['status']=='ready'
                print('Clean-user MCP startup, dynamic account discovery, selected-sender draft, invalid sender rejection and Inbox account schemas passed. No credentials accessed or email sent.')
asyncio.run(main())
