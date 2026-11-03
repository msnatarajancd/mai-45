"""Semantic palettes; only presentation changes when appearance switches."""
PALETTES = {
    'Bright': dict(bg='#f8f9f5',surface='#ffffff',soft='#edf2e9',ink='#183c36',muted='#60756b',border='#cddbd0',accent='#167367',onaccent='#ffffff',link='#116b60',warn='#fff1d7',warntext='#765019',emergency='#fff4ee',danger='#8c3d32',shadow='#163b3529',info='#e6f1f5'),
    'Dark': dict(bg='#101b19',surface='#192b26',soft='#223b32',ink='#ecf4ed',muted='#b4c8ba',border='#456257',accent='#94d2ad',onaccent='#10291f',link='#a1dfbc',warn='#44351c',warntext='#f4d393',emergency='#392722',danger='#ffc1ad',shadow='#00000066',info='#223d47'),
}


def theme_variables(appearance):
    colors=PALETTES.get(appearance,PALETTES['Bright'])
    values=';'.join('--rr-'+k+':'+v for k,v in colors.items())
    scheme='dark' if appearance=='Dark' else 'light'
    return ':root{'+values+';color-scheme:'+scheme+';}'
