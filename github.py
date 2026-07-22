from __future__ import annotations
import asyncio, base64, random
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
import aiohttp

@dataclass(slots=True)
class GitHubError(Exception):
    message: str; status: int=0; retry_after: float|None=None
    def __str__(self)->str: return self.message

class GitHubClient:
    API="https://api.github.com"
    def __init__(self, token:str, timeout:float=60):
        self.token=token; self.timeout=aiohttp.ClientTimeout(total=timeout,connect=15)
        self.session:aiohttp.ClientSession|None=None
    async def __aenter__(self):
        self.session=aiohttp.ClientSession(timeout=self.timeout,headers={"Authorization":f"Bearer {self.token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"zip-github-telegram-bot"}); return self
    async def __aexit__(self,*_:object):
        if self.session: await self.session.close()
    async def request(self,method:str,path:str,*,json:dict[str,Any]|None=None,retries:int=3)->Any:
        assert self.session
        for attempt in range(retries+1):
            try:
                async with self.session.request(method,self.API+path,json=json) as res:
                    data=await res.json(content_type=None) if res.status!=204 else {}
                    if 200<=res.status<300: return data
                    msg=data.get('message',res.reason) if isinstance(data,dict) else res.reason
                    retry=float(res.headers.get('Retry-After','0') or 0)
                    reset=res.headers.get('X-RateLimit-Reset')
                    if res.status in {403,429} and ('rate limit' in msg.lower() or retry or res.headers.get('X-RateLimit-Remaining')=='0'):
                        import time
                        wait=retry or (max(1,float(reset)-time.time()) if reset else 15)
                        if attempt<retries: await asyncio.sleep(min(wait,120)); continue
                        raise GitHubError(msg,res.status,wait)
                    if res.status>=500 and attempt<retries:
                        await asyncio.sleep((2**attempt)+random.random()); continue
                    raise GitHubError(msg,res.status)
            except (aiohttp.ClientError,asyncio.TimeoutError) as exc:
                if attempt>=retries: raise GitHubError(str(exc)) from exc
                await asyncio.sleep((2**attempt)+random.random())
        raise GitHubError('GitHub request failed')
    async def user(self)->dict[str,Any]: return await self.request('GET','/user')
    async def create_repo(self,name:str,private:bool,description:str)->dict[str,Any]: return await self.request('POST','/user/repos',json={'name':name,'private':private,'description':description,'auto_init':False})
    async def repo(self,owner:str,name:str)->dict[str,Any]: return await self.request('GET',f'/repos/{owner}/{name}')
    async def ref(self,owner:str,repo:str,branch:str)->dict[str,Any]: return await self.request('GET',f'/repos/{owner}/{repo}/git/ref/heads/{quote(branch,safe="")}')
    async def create_branch(self,owner:str,repo:str,branch:str,from_branch:str)->None:
        source=await self.ref(owner,repo,from_branch); await self.request('POST',f'/repos/{owner}/{repo}/git/refs',json={'ref':f'refs/heads/{branch}','sha':source['object']['sha']})
    async def content(self,owner:str,repo:str,path:str,branch:str)->dict[str,Any]|None:
        try: return await self.request('GET',f'/repos/{owner}/{repo}/contents/{quote(path,safe="/")}?ref={quote(branch,safe="")}',retries=1)
        except GitHubError as exc:
            if exc.status==404:return None
            raise
    async def put_file(self,owner:str,repo:str,path:str,branch:str,content:bytes,message:str,retries:int,omit_branch:bool=False)->dict[str,Any]:
        existing=None if omit_branch else await self.content(owner,repo,path,branch)
        body={'message':message,'content':base64.b64encode(content).decode()}
        if not omit_branch: body['branch']=branch
        if existing and existing.get('sha'): body['sha']=existing['sha']
        return await self.request('PUT',f'/repos/{owner}/{repo}/contents/{quote(path,safe="/")}',json=body,retries=retries)
