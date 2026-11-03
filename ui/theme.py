"""Semantic palettes shared by the application and accessible tour controls."""
PALETTES = {
 'Bright': dict(bg='#f4f6fa',surface='#ffffff',soft='#edf2f5',ink='#182735',muted='#5f6f7e',border='#dce4ea',accent='#087f6c',onaccent='#ffffff',link='#087565',warn='#fff4dc',warntext='#76520f',emergency='#fff5f2',danger='#a23c32',shadow='#1a334c12',info='#eaf3fa',sidebar='#edf1f6',selected='#dcefe9'),
 'Dark': dict(bg='#0d141e',surface='#172230',soft='#202f40',ink='#f1f6fa',muted='#b1c0cf',border='#344558',accent='#65dbba',onaccent='#092d24',link='#77e4c5',warn='#3c321f',warntext='#f2d492',emergency='#342329',danger='#ffb3a5',shadow='#00000045',info='#1e3448',sidebar='#111b27',selected='#24473f'),
}

def theme_variables(appearance):
 colors=PALETTES.get(appearance,PALETTES['Bright'])
 values=';'.join('--rr-'+k+':'+v for k,v in colors.items())
 return ':root{'+values+';color-scheme:'+('dark' if appearance=='Dark' else 'light')+';}'
