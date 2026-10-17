"""Settings for real SSIDs; credentials remain in Windows saved profiles."""
import tkinter as tk
from tkinter import ttk, messagebox
from wifi_networks import WindowsWifi, save_settings


def open_settings(app):
    if getattr(app, 'settings_window', None) is not None and app.settings_window.winfo_exists():
        app.settings_window.lift()
        return
    window = tk.Toplevel(app.root)
    app.settings_window = window
    window.title('Settings — Redes Wi-Fi')
    window.geometry('760x600')
    window.minsize(700, 560)
    window.transient(app.root)
    frame = ttk.Frame(window, padding=14)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(1, weight=1)
    ttk.Label(frame, text='Adicione os nomes reais das redes (SSID), exatamente como aparecem no Wi-Fi do Windows.\n'
              'Conecte a cada uma pelo Windows uma vez e deixe a senha salva.', wraplength=700).grid(
                  row=0, column=0, columnspan=3, sticky='w', pady=(0,10))
    ttk.Label(frame, text='Adaptador Wi-Fi').grid(row=1, column=0, sticky='w')
    adapter_var = tk.StringVar()
    adapter = ttk.Combobox(frame, textvariable=adapter_var, state='readonly')
    adapter.grid(row=1, column=1, sticky='ew', padx=6)
    adapters, saved = {}, {}
    networks = [dict(item) for item in app.wifi_settings['networks']]
    ssid_var = tk.StringVar()
    ttk.Label(frame, text='Nome real da rede (SSID)').grid(row=2, column=0, sticky='w', pady=(12,0))
    ssid_entry = ttk.Combobox(frame, textvariable=ssid_var, state='normal')
    ssid_entry.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=(12,0))
    ttk.Label(frame, text='Digite o nome ou selecione uma rede detectada. Não use apelidos.').grid(
        row=3, column=1, columnspan=2, sticky='w', padx=6)
    table = ttk.Treeview(frame, columns=('ssid',), show='headings', height=5, selectmode='browse')
    table.heading('ssid', text='Redes Wi-Fi para alternar — nomes reais (SSID)')
    table.column('ssid', width=620)
    table.grid(row=5, column=0, columnspan=3, sticky='nsew', pady=8)
    frame.rowconfigure(5, weight=1)

    def draw():
        table.delete(*table.get_children())
        for n, item in enumerate(networks):
            table.insert('', 'end', iid=str(n), values=(item['ssid'],))

    def select(event=None):
        chosen = table.selection()
        if chosen: ssid_var.set(networks[int(chosen[0])]['ssid'])
    table.bind('<<TreeviewSelect>>', select)

    def add():
        ssid = ssid_var.get()  # SSIDs can legitimately include leading/trailing spaces.
        if ssid not in saved:
            messagebox.showerror('Redes', 'Não há perfil salvo para esta rede neste adaptador.\n'
                'Conecte ao nome real pelo Wi-Fi do Windows, salve a senha e clique em Atualizar redes.', parent=window)
            return
        chosen = table.selection()
        index = int(chosen[0]) if chosen else None
        if any(n != index and item['ssid'] == ssid for n,item in enumerate(networks)):
            messagebox.showerror('Redes', 'Esta rede já foi adicionada.', parent=window)
            return
        item = dict(ssid=ssid, profile=saved[ssid])
        if index is None: networks.append(item)
        else: networks[index] = item
        draw(); ssid_var.set('')

    def remove():
        chosen = table.selection()
        if chosen:
            networks.pop(int(chosen[0])); draw(); ssid_var.set('')

    def clear():
        table.selection_remove(*table.selection()); ssid_var.set('')

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=3, sticky='w', pady=6)
    ttk.Button(buttons, text='Adicionar / atualizar', command=add).pack(side='left')
    ttk.Button(buttons, text='Nova rede', command=clear).pack(side='left', padx=6)
    ttk.Button(buttons, text='Remover selecionada', command=remove).pack(side='left')
    hint = tk.StringVar(value='')
    ttk.Label(frame, textvariable=hint, wraplength=700).grid(row=6,column=0,columnspan=3,sticky='w')

    def refresh_networks(event=None):
        wifi = None
        try:
            wifi = WindowsWifi()
            key = adapters[adapter_var.get()]
            saved.clear()
            for item in wifi.saved_networks(key):
                saved[item['ssid']] = item['profile']
            try:
                available = wifi.available(key)
                ssid_entry.configure(values=available)
                hint.set('Redes detectadas: ' + str(len(available)) + '. Você também pode digitar o SSID de uma rede salva.')
            except OSError:
                ssid_entry.configure(values=list(saved))
                hint.set('Lista de redes detectadas indisponível. Digite o SSID real; perfis salvos disponíveis na lista.')
        except Exception as error:
            saved.clear(); ssid_entry.configure(values=[])
            hint.set('Não foi possível ler as redes: ' + str(error))
        finally:
            if wifi: wifi.close()

    def refresh():
        wifi = None
        old_key = adapters.get(adapter_var.get(), app.wifi_settings['interface'])
        try:
            wifi = WindowsWifi()
            adapters.clear()
            for item in wifi.interfaces():
                adapters[item.description + ' [' + item.guid.key()[:8] + ']'] = item.guid.key()
            adapter.configure(values=list(adapters))
            adapter_var.set(next((name for name, guid in adapters.items() if guid == old_key), next(iter(adapters), '')))
            if not adapters:
                raise OSError('Nenhum adaptador Wi-Fi encontrado. Ative o Wi-Fi no Windows.')
        except Exception as error:
            hint.set(str(error)); return
        finally:
            if wifi: wifi.close()
        refresh_networks()

    adapter.bind('<<ComboboxSelected>>', refresh_networks)
    ttk.Button(frame, text='Atualizar redes', command=refresh).grid(row=1, column=2)
    mode = tk.StringVar(value=app.wifi_settings['mode'])
    interval = tk.StringVar(value=str(app.wifi_settings['interval']))
    options = ttk.LabelFrame(frame, text='Quando alternar (na ordem da lista)', padding=10)
    options.grid(row=7, column=0, columnspan=3, sticky='ew',pady=(8,0))
    ttk.Radiobutton(options, text='Desligado — manter a rede atual', variable=mode, value='off').grid(row=0,column=0,columnspan=3,sticky='w')
    ttk.Radiobutton(options, text='A cada', variable=mode, value='interval').grid(row=1,column=0,sticky='w')
    ttk.Entry(options, textvariable=interval, width=9).grid(row=1,column=1,padx=6)
    ttk.Label(options, text='segundos').grid(row=1,column=2,sticky='w')
    ttk.Radiobutton(options, text='Se a verificação não iniciar em 2 segundos após carregar o formulário',
                    variable=mode, value='stalled').grid(row=2,column=0,columnspan=3,sticky='w',pady=(6,0))
    ttk.Label(frame, text='O desafio aberto continua manual. A troca fecha o navegador e retoma o CPF pendente.\n'
              'Duas redes podem usar o mesmo IP público. Configurações valem no próximo Iniciar.',
              wraplength=700).grid(row=8,column=0,columnspan=3,sticky='w',pady=10)

    def save():
        try:
            settings = dict(mode=mode.get(), interval=interval.get().replace(',', '.'),
                            interface=adapters.get(adapter_var.get(), ''), networks=networks)
            if settings['mode'] != 'off':
                if any(item['ssid'] not in saved for item in networks):
                    raise ValueError('Uma das redes não está salva neste adaptador. Atualize as redes.')
                settings['networks'] = [dict(ssid=item['ssid'], profile=saved[item['ssid']]) for item in networks]
            app.wifi_settings = save_settings(app.wifi_settings_path, settings)
            app.status.config(text='Configurações Wi-Fi salvas; serão usadas no próximo Iniciar.')
            window.destroy()
        except (ValueError, OSError) as error:
            messagebox.showerror('Settings', str(error), parent=window)

    footer = ttk.Frame(frame)
    footer.grid(row=9,column=0,columnspan=3,sticky='e')
    ttk.Button(footer,text='Cancelar',command=window.destroy).pack(side='left',padx=6)
    ttk.Button(footer,text='Salvar',command=save).pack(side='left')
    draw(); refresh()
