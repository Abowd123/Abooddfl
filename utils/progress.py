def bar(percent:float,width:int=16)->str:
 filled=min(width,max(0,round(percent*width/100)));return '█'*filled+'░'*(width-filled)
def duration(seconds:float)->str:
 seconds=int(max(0,seconds));m,s=divmod(seconds,60);h,m=divmod(m,60)
 return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'
