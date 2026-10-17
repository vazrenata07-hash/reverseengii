"""The compact preview runs a regular browser outside the visible desktop."""
def browser_args(exe,port,profile,url,compact=False):
    args=[exe,f'--remote-debugging-port={port}',f'--user-data-dir={profile}',
          '--no-first-run','--no-default-browser-check','--disable-background-networking',
          '--disable-component-update','--disable-sync','--disable-default-apps',
          '--disable-domain-reliability','--disk-cache-size=134217728']
    if compact:
        return args+[f'--app={url}','--window-size=1280,900','--window-position=-32000,-32000',
                     '--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding']
    return args+['--new-window',url]
