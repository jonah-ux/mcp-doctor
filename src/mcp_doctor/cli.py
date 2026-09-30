import argparse,json,sys

def main(argv=None):
 p=argparse.ArgumentParser(prog="mcp-doctor",description="MCP server contract linter"); p.add_argument("command",choices=["check"]); p.add_argument("path",nargs="?"); p.add_argument("--json",action="store_true"); a=p.parse_args(argv)
 data=json.load(open(a.path)) if a.path else {"tools":[],"resources":[],"prompts":[]}; findings=[]
 for group in ("tools","resources","prompts"):
  for item in data.get(group,[]):
   if not item.get("name"): findings.append({"code":"MCP001","path":group,"message":"missing name"})
   if group=="tools" and not item.get("description"): findings.append({"code":"MCP002","path":item.get("name","?"),"message":"tool needs a description"})
   if group=="tools" and "inputSchema" not in item: findings.append({"code":"MCP003","path":item.get("name","?"),"message":"tool needs inputSchema"})
   if item.get("timeout") is None and group=="tools": findings.append({"code":"MCP004","path":item.get("name","?"),"message":"declare a timeout"})
 out={"schema":"mcp-doctor/v1","ok":not findings,"findings":findings,"counts":{"tools":len(data.get("tools",[])),"resources":len(data.get("resources",[])),"prompts":len(data.get("prompts",[]))}}
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["ok"] else 1
