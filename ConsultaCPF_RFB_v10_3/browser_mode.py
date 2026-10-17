"""Visible full-browser and compact application-window launch modes."""
def browser_args(exe, port, profile, url, compact=False):
    args = [exe, f'--remote-debugging-port={port}', f'--user-data-dir={profile}',
            '--no-first-run', '--no-default-browser-check',
            '--disable-background-networking', '--disable-component-update',
            '--disable-sync', '--disable-default-apps', '--disable-domain-reliability',
            '--disk-cache-size=134217728']
    if compact:
        return args + [f'--app={url}', '--window-size=350,150', '--window-position=0,0']
    return args + ['--new-window', url]
