import json,tempfile,pathlib
from mcp_doctor.cli import main
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'server.json'; p.write_text(json.dumps({'tools':[{'name':'search','description':'Find things','inputSchema':{},'timeout':5}], 'resources':[], 'prompts':[]}))
 print('MCP Doctor demo: a clean contract is boring on purpose')
 main(['check',str(p)])
