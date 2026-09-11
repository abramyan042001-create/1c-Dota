"""Запуск: python app.py. Python 3.10+, стандартная библиотека."""
import copy
import csv
import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from datetime import datetime
from model import Database, SCHEMAS, CHILDREN, LABELS, ENTITIES, STYLES

BG='#1B1E21'; PANEL='#2F363D'; GOLD='#DAA520'
COLORS={'Сила':'#EF995C','Ловкость':'#83CE7D','Интеллект':'#72BFE8','Универсал':'#B9A2FF','Radiant':'#A7CF65','Dire':'#F28B63'}

class Editor(tk.Toplevel):
    def __init__(self,app,kind,data,callback):
        super().__init__(app.root)
        self.app=app; self.kind=kind; self.callback=callback; self.data=copy.deepcopy(data or {})
        self.title(LABELS[kind]); self.geometry('850x720'); self.configure(bg=BG)
        self.transient(app.root); self.grab_set()
        self.vars={}; self.maps={}; self.tables={}
        frame=ttk.Frame(self,padding=16); frame.pack(fill='both',expand=True)
        for row,(key,label,spec) in enumerate(SCHEMAS[kind]):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=3)
            default=1 if key in ('difficulty','priority','slot','order','duration') else 0
            if spec=='bool':
                var=tk.BooleanVar(value=self.data.get(key,key=='active')); widget=ttk.Checkbutton(frame,variable=var)
            else:
                value=self.data.get(key,default if spec=='int' else datetime.now().strftime('%Y-%m-%d %H:%M') if key=='date' else '')
                if isinstance(spec,list):
                    var=tk.StringVar(value=value or spec[0]); widget=ttk.Combobox(frame,textvariable=var,values=spec,state='readonly')
                elif spec.startswith(('@','?')):
                    mapping={r['name']+' ['+r['id']+']':r['id'] for r in app.db.all(spec[1:])}
                    if spec.startswith('?'): mapping={'—':'',**mapping}
                    self.maps[key]=mapping
                    selected=next((n for n,i in mapping.items() if i==value),'')
                    var=tk.StringVar(value=selected); widget=ttk.Combobox(frame,textvariable=var,values=list(mapping),state='readonly')
                else:
                    var=tk.StringVar(value=value); widget=ttk.Entry(frame,textvariable=var)
            self.vars[key]=var; widget.grid(row=row,column=1,sticky='ew',padx=10,pady=3)
        frame.columnconfigure(1,weight=1)
        childnames=CHILDREN.get(kind,[])
        if childnames:
            tabs=ttk.Notebook(frame); tabs.grid(row=len(SCHEMAS[kind]),column=0,columnspan=2,sticky='nsew',pady=12)
            frame.rowconfigure(len(SCHEMAS[kind]),weight=1)
            for child in childnames:
                self.data.setdefault(child,[])
                pane=ttk.Frame(tabs); tabs.add(pane,text=LABELS[child])
                tree=app.table(pane,[f[1] for f in SCHEMAS[child]])
                self.tables[child]=tree
                bar=ttk.Frame(pane); bar.pack(fill='x')
                ttk.Button(bar,text='Добавить',command=lambda c=child:self.edit_child(c)).pack(side='left')
                ttk.Button(bar,text='Изменить',command=lambda c=child:self.edit_child(c,True)).pack(side='left')
                ttk.Button(bar,text='Удалить',command=lambda c=child:self.remove_child(c)).pack(side='left')
                self.refresh_child(child)
        ttk.Button(frame,text='Сохранить',command=self.save).grid(row=len(SCHEMAS[kind])+1,column=1,sticky='e',pady=12)

    def refresh_child(self,child):
        tree=self.tables[child]; tree.delete(*tree.get_children())
        for i,r in enumerate(self.data[child]): tree.insert('', 'end',iid=str(i),values=self.app.values(child,r))

    def edit_child(self,child,existing=False):
        selection=self.tables[child].selection()
        if existing and not selection: return
        index=int(selection[0]) if existing else None
        def done(data):
            if index is None: self.data[child].append(data)
            else: self.data[child][index]=data
            self.refresh_child(child); self.grab_set()
        Editor(self.app,child,self.data[child][index] if index is not None else None,done)

    def remove_child(self,child):
        selected=self.tables[child].selection()
        if selected: self.data[child].pop(int(selected[0])); self.refresh_child(child)

    def save(self):
        try:
            result=copy.deepcopy(self.data)
            for key,label,spec in SCHEMAS[self.kind]:
                value=self.vars[key].get()
                if spec=='int': value=int(value)
                elif key in self.maps: value=self.maps[key].get(value,'')
                result[key]=value
            self.app.db.validate(self.kind,result)
            self.callback(result); self.destroy()
        except (ValueError,sqlite3.Error,KeyError) as exc: messagebox.showerror('Проверка данных',str(exc),parent=self)

class App:
    def __init__(self,root,db):
        self.root=root; self.db=db; self.actor=None
        root.title('FAN DOTA2'); root.geometry('1180x780'); root.configure(bg=BG)
        style=ttk.Style(); style.theme_use('clam')
        style.configure('.',background=BG,foreground='#F3F0E9',fieldbackground=PANEL)
        style.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground='#F3F0E9',rowheight=29)
        style.configure('Treeview.Heading',background=BG,foreground=GOLD)
        style.map('Treeview',background=[('selected','#A83806')])
        style.configure('TButton',padding=7,background=PANEL,foreground=GOLD)
        style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly','#FFFFFF')])
        root.option_add('*TCombobox*Listbox.background',PANEL); root.option_add('*TCombobox*Listbox.foreground','white')
        self.login_screen()

    def error(self,fn):
        try: return fn()
        except (ValueError,KeyError,TypeError,sqlite3.Error,OSError) as exc: messagebox.showerror('Ошибка',str(exc),parent=self.root)

    def login_screen(self):
        setup=not self.db.db.execute('SELECT 1 FROM users LIMIT 1').fetchone()
        pane=ttk.Frame(self.root,padding=40); pane.pack(expand=True)
        ttk.Label(pane,text='FAN DOTA2',font=('Arial',28,'bold'),foreground=GOLD).pack(pady=20)
        ttk.Label(pane,text='Создайте администратора' if setup else 'Вход в программу').pack()
        login=tk.StringVar(value='Admin'); password=tk.StringVar()
        ttk.Entry(pane,textvariable=login).pack(pady=10)
        ttk.Entry(pane,textvariable=password,show='*').pack(pady=10)
        ttk.Label(pane,text='Пароль от 8 символов' if setup else '').pack()
        def submit():
            if setup: self.db.add_user(login.get(),password.get(),'Admin')
            self.role=self.db.login(login.get(),password.get()); self.actor=login.get(); pane.destroy(); self.main()
        ttk.Button(pane,text='Создать и войти' if setup else 'Войти',command=lambda:self.error(submit)).pack(pady=12)

    def table(self,parent,columns):
        box=ttk.Frame(parent); box.pack(fill='both',expand=True)
        tree=ttk.Treeview(box,columns=list(range(len(columns))),show='headings',selectmode='browse')
        for i,title in enumerate(columns): tree.heading(i,text=title); tree.column(i,width=155,minwidth=90)
        y=ttk.Scrollbar(box,orient='vertical',command=tree.yview); x=ttk.Scrollbar(box,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        tree.grid(row=0,column=0,sticky='nsew'); y.grid(row=0,column=1,sticky='ns'); x.grid(row=1,column=0,sticky='ew')
        box.rowconfigure(0,weight=1); box.columnconfigure(0,weight=1)
        return tree

    def values(self,kind,data):
        out=[]
        for key,label,spec in SCHEMAS[kind]:
            value=data.get(key,'')
            if isinstance(spec,str) and spec.startswith(('@','?')): value=self.db.name(spec[1:],value)
            elif spec=='bool': value='Да' if value else 'Нет'
            out.append(value)
        return out

    def main(self):
        ttk.Label(self.root,text='FAN DOTA2  /  '+self.actor,font=('Arial',23,'bold'),foreground=GOLD,padding=16).pack(anchor='w')
        ttk.Label(self.root,text='Офлайн-справочник • учебные данные • статистика только проведённых матчей',padding=8).pack(anchor='w')
        self.tabs=ttk.Notebook(self.root); self.tabs.pack(fill='both',expand=True,padx=12,pady=12)
        self.trees={}; self.filters={}
        for kind in ENTITIES:
            pane=ttk.Frame(self.tabs); self.tabs.add(pane,text=LABELS[kind])
            bar=ttk.Frame(pane,padding=6); bar.pack(fill='x')
            query=tk.StringVar(); self.filters[kind]=query
            ttk.Label(bar,text='Поиск / фильтр:').pack(side='left'); ttk.Entry(bar,textvariable=query,width=24).pack(side='left',padx=6)
            query.trace_add('write',lambda *_,k=kind:self.refresh(k))
            can_edit=self.role=='Admin' or kind in ['builds','players','matches']
            for title,fn in [('Добавить',lambda k=kind:self.edit(k)),('Изменить',lambda k=kind:self.edit(k,True)),('Удалить',lambda k=kind:self.delete(k))]:
                ttk.Button(bar,text=title,command=lambda f=fn:self.error(f),state='normal' if can_edit else 'disabled').pack(side='left',padx=3)
            if kind=='matches':
                for title,posted in [('Провести',True),('Отменить проведение',False)]: ttk.Button(bar,text=title,command=lambda p=posted:self.error(lambda:self.post(p))).pack(side='left')
            columns=[f[1] for f in SCHEMAS[kind]]+(['Статус'] if kind=='matches' else [])
            tree=self.table(pane,columns); self.trees[kind]=tree
            for tag,color in COLORS.items(): tree.tag_configure(tag,foreground=color)
            self.refresh(kind)
        self.calc_tab(); self.report_tab(); self.admin_tab()

    def refresh(self,kind=None):
        for k in ([kind] if kind else ENTITIES):
            tree=self.trees[k]; tree.delete(*tree.get_children()); q=self.filters[k].get().casefold()
            for r in self.db.all(k):
                values=self.values(k,r)
                if k=='matches': values+=['Проведён' if r.get('posted') else 'Черновик']
                if q not in ' '.join(map(str,values)).casefold(): continue
                tree.insert('','end',iid=r['id'],values=values,tags=(r.get('attribute',r.get('side','')),))

    def selected(self,kind):
        s=self.trees[kind].selection()
        if not s: raise ValueError('Выберите строку в таблице')
        return s[0]

    def edit(self,kind,existing=False):
        data=self.db.get(kind,self.selected(kind)) if existing else None
        def done(record): self.db.save(kind,record,self.actor); self.refresh()
        Editor(self,kind,data,done)

    def delete(self,kind):
        ident=self.selected(kind)
        if messagebox.askyesno('Удаление','Удалить выбранную запись?'):
            self.db.delete(kind,ident,self.actor); self.refresh()

    def post(self,posted): self.db.post(self.selected('matches'),posted,self.actor); self.refresh('matches'); self.show_reports()

    def calc_tab(self):
        pane=ttk.Frame(self.tabs,padding=12); self.tabs.add(pane,text='Калькулятор')
        hero=tk.StringVar(); style=tk.StringVar(value=STYLES[0])
        hc=ttk.Combobox(pane,textvariable=hero,state='readonly',postcommand=lambda:hc.configure(values=[r['name'] for r in self.db.all('heroes')]))
        ttk.Label(pane,text='Герой').pack(anchor='w'); hc.pack(fill='x')
        ttk.Label(pane,text='Тип сборки').pack(anchor='w'); ttk.Combobox(pane,textvariable=style,values=STYLES,state='readonly').pack(fill='x')
        output=tk.Text(pane,bg=PANEL,fg='white',wrap='word',font=('Arial',12)); output.pack(fill='both',expand=True,pady=10)
        def calc():
            output.config(state='normal'); output.delete('1.0','end')
            found=False
            for b in self.db.all('builds'):
                if self.db.name('heroes',b['hero'])!=hero.get() or b['style']!=style.get(): continue
                found=True; total,tips=self.db.calculate(b['id']); output.insert('end',b['name']+'\n')
                for s in sorted(b['slots'],key=lambda s:s['order']):
                    i=self.db.get('items',s['item']); output.insert('end',f"Слот {s['slot']} · {i['name']} · {i['price']} золота\n")
                output.insert('end',f'Итого: {total} золота\n'+('; '.join(tips) or 'Базовые проверки пройдены')+'\n\n')
            if not found: output.insert('end','Сборки не найдены. Создайте сборку или загрузите демо-данные.')
            output.insert('end','\nПодсказки — простые учебные правила, не оценка игровой стратегии.'); output.config(state='disabled')
        ttk.Button(pane,text='Рассчитать',command=lambda:self.error(calc)).pack(anchor='e')

    def report_tab(self):
        pane=ttk.Frame(self.tabs); self.tabs.add(pane,text='Отчёты')
        bar=ttk.Frame(pane); bar.pack(fill='x'); self.report_style=tk.StringVar(value='Все')
        ttk.Combobox(bar,textvariable=self.report_style,values=['Все']+STYLES,state='readonly').pack(side='left')
        ttk.Button(bar,text='Обновить отчёты',command=lambda:self.error(self.show_reports)).pack(side='left')
        ttk.Button(bar,text='Экспорт текущего отчёта CSV',command=lambda:self.error(self.export_report)).pack(side='left')
        self.report_tabs=ttk.Notebook(pane); self.report_tabs.pack(fill='both',expand=True)
        self.report_headers=[['Герой','Игрок','Игр','Побед','Винрейт, %','Средний KDA'],['Предмет','Герой','Игрок','Количество'],['Сборка','Герой','Стиль','Цена']]
        self.report_trees=[]
        for title,headers in zip(['Винрейт по героям и игрокам','Популярные предметы','Сборки по стилю'],self.report_headers):
            tab=ttk.Frame(self.report_tabs); self.report_tabs.add(tab,text=title); self.report_trees.append(self.table(tab,headers))
        self.show_reports()

    def show_reports(self):
        wins,purchases=self.db.reports()
        builds=[(b['name'],self.db.name('heroes',b['hero']),b['style'],self.db.calculate(b['id'])[0]) for b in self.db.all('builds') if self.report_style.get() in ('Все',b['style'])]
        for tree,rows in zip(self.report_trees,[wins,purchases,builds]):
            tree.delete(*tree.get_children())
            for row in rows: tree.insert('','end',values=row)

    def export_report(self):
        self.show_reports(); index=self.report_tabs.index('current')
        path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if path:
            with open(path,'w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f,delimiter=';'); writer.writerow(self.report_headers[index]); tree=self.report_trees[index]
                writer.writerows(tree.item(i,'values') for i in tree.get_children())

    def admin_tab(self):
        pane=ttk.Frame(self.tabs,padding=24); self.tabs.add(pane,text='Администрирование')
        ttk.Label(pane,text='25 героев, 12 предметов, 3 сборки, игрок «Я». Повторная загрузка не создаёт дубликаты.').pack(anchor='w',pady=10)
        def seed(): self.db.seed(self.actor); self.refresh(); self.show_reports(); messagebox.showinfo('Готово','Демо-данные загружены')
        for title,fn in [('Загрузить демо-данные',seed),('Импорт JSON (объединение по ID)',self.import_json),('Добавить пользователя',self.new_user)]:
            ttk.Button(pane,text=title,command=lambda f=fn:self.error(f),state='normal' if self.role=='Admin' else 'disabled').pack(anchor='w',pady=6)
        ttk.Button(pane,text='Экспорт всех данных JSON',command=lambda:self.error(self.export_json)).pack(anchor='w',pady=6)
        ttk.Label(pane,text='Участники матча — игроки вашей стороны. Победа относится ко всем участникам.\nРезервная копия: закройте программу и скопируйте файл fan_dota2.sqlite3.\nПароли пользователей не входят в экспорт JSON.').pack(anchor='w',pady=20)

    def export_json(self):
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if path: Path(path).write_text(json.dumps(self.db.export_data(),ensure_ascii=False,indent=2),encoding='utf-8')

    def import_json(self):
        path=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if path and messagebox.askyesno('Импорт','Записи с совпадающим ID будут заменены. Продолжить?'):
            self.db.import_data(json.loads(Path(path).read_text(encoding='utf-8')),self.actor); self.refresh(); self.show_reports()

    def new_user(self):
        name=simpledialog.askstring('Пользователь','Логин:')
        if not name: return
        password=simpledialog.askstring('Пользователь','Пароль (минимум 8 символов):',show='*')
        if password is None: return
        role=simpledialog.askstring('Пользователь','Роль: Admin или Player',initialvalue='Player')
        if role is None: return
        self.db.add_user(name,password,role,self.actor); messagebox.showinfo('Готово','Пользователь добавлен')

if __name__=='__main__':
    db=Database(Path(__file__).resolve().parent/'fan_dota2.sqlite3')
    root=tk.Tk(); app=App(root,db)
    root.mainloop(); db.db.close()
