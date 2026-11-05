"""Semantic palettes shared by the application and accessible tour controls."""
PALETTES = {
 'Bright': dict(bg='#f7f8fc',surface='#ffffff',soft='#eef2f8',ink='#172b4d',muted='#52627a',border='#dce3ee',accent='#2457c5',onaccent='#ffffff',link='#204fae',warn='#fff4dc',warntext='#76520f',emergency='#fff5f2',danger='#a23c32',shadow='#1a334c12',info='#eaf3fa',sidebar='#eef2f8',selected='#e7eefc'),
 'Dark': dict(bg='#0d141e',surface='#172230',soft='#202f40',ink='#f1f6fa',muted='#b1c0cf',border='#344558',accent='#9bbcff',onaccent='#101f3d',link='#abc8ff',warn='#3c321f',warntext='#f2d492',emergency='#342329',danger='#ffb3a5',shadow='#00000045',info='#1e3448',sidebar='#111b27',selected='#263f66'),
}

def theme_variables(appearance):
 colors=PALETTES.get(appearance,PALETTES['Bright'])
 values=';'.join('--rr-'+k+':'+v for k,v in colors.items())
 return ':root{'+values+';color-scheme:'+('dark' if appearance=='Dark' else 'light')+';}'
