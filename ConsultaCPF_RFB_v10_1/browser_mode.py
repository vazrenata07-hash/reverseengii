"""Standard browser launch modes; no changes to verification or browser identity."""
import time

class HeadlessNeedsWindow(RuntimeError):
    pass

def browser_args(exe, port, profile, url, headless=False):
    args = [exe, f'--remote-debugging-port={port}', f'--user-data-dir={profile}',
            '--no-first-run', '--no-default-browser-check',
            '--disable-background-networking', '--disable-component-update',
            '--disable-sync', '--disable-default-apps', '--disable-domain-reliability',
            '--disk-cache-size=134217728']
    if headless:
        args += ['--headless=new', '--window-size=1280,900']
    else:
        args += ['--new-window']
    return args + [url]

def check_headless_progress(headless, loaded_at, token_ready, submitted, now=None):
    if (headless and loaded_at is not None and not token_ready and not submitted
            and (time.monotonic() if now is None else now) - loaded_at >= 30):
        raise HeadlessNeedsWindow('Teste sem janela: a verificação não liberou a consulta em 30 segundos. '
                                  'Resultados preservados. Em Settings, desmarque Navegador sem janela '
                                  'e clique em Iniciar para continuar com o navegador visível.')
