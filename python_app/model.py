"""FAN DOTA2: domain model, SQLite storage and reports (standard library only)."""
import copy
import hashlib
import hmac
import json
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime

ATTRIBUTES = ['Сила', 'Ловкость', 'Интеллект', 'Универсал']
ROLES = ['Carry', 'Mid', 'Offlane', 'SoftSupport', 'HardSupport']
STYLES = ['Крит', 'Живучесть', 'Скорость', 'Универсальная', 'Саппорт']
CATEGORIES = ['Boots','Farming','Mobility','Survivability','CritDPS','AttackSpeed','Utility','Aura','Consumable','Neutral']
# Fields: name, caption, type/default or enumeration/reference.
SCHEMAS = {
 'heroes': [('name','Имя','str'),('attribute','Атрибут',ATTRIBUTES),('difficulty','Сложность (1–3)','int'),('description','Описание','str'),('hp','Базовое HP','int'),('speed','Базовая скорость','int'),('active','Активен','bool')],
 'items': [('name','Название','str'),('category','Категория / группа',CATEGORIES),('price','Цена','int'),('description','Описание','str'),('crit','Даёт крит','bool'),('speed','Даёт скорость','bool'),('survival','Даёт живучесть','bool'),('ability','Активная способность','bool')],
 'players': [('name','Ник','str'),('role','Основная роль',ROLES),('style','Любимый стиль',STYLES),('comment','Комментарий','str')],
 'builds': [('name','Название','str'),('hero','Герой','@heroes'),('style','Тип сборки',STYLES),('role','Роль',ROLES),('description','Описание','str'),('situation','Ситуация','str')],
 'matches': [('name','Название','str'),('date','Дата (ГГГГ-ММ-ДД ЧЧ:ММ)','str'),('side','Наша сторона',['Radiant','Dire']),('win','Победа нашей стороны','bool'),('duration','Длительность, мин','int'),('patch','Патч','str'),('comment','Комментарий','str')],
 'roles': [('role','Роль',ROLES),('priority','Приоритет (1–9)','int')],
 'slots': [('slot','Слот (1–6)','int'),('item','Предмет','@items'),('order','Порядок покупки','int'),('required','Обязательный','bool'),('comment','Комментарий','str')],
 'participants': [('player','Игрок','@players'),('hero','Герой','@heroes'),('role','Роль',ROLES),('kills','Убийства','int'),('deaths','Смерти','int'),('assists','Помощи','int'),('networth','Нетворс','int'),('build','План сборки (необязательно)','?builds')],
 'purchases': [('player','Игрок','@players'),('item','Предмет','@items'),('minute','Минута покупки','int')]
}
CHILDREN = {'heroes':['roles'], 'builds':['slots'], 'matches':['participants','purchases']}
LABELS = {'heroes':'Герои','items':'Предметы','players':'Игроки','builds':'Сборки','matches':'Матчи','roles':'Роли','slots':'Слоты','participants':'Участники','purchases':'Покупки'}
ENTITIES = ['heroes','items','players','builds','matches']

class Database:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY, salt TEXT, digest TEXT, role TEXT)')
        self.db.commit()

    def all(self, kind):
        return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid',(kind,))]

    def get(self, kind, ident):
        row = self.db.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,ident)).fetchone()
        if not row:
            raise ValueError('Не найдена ссылка: '+LABELS.get(kind,kind))
        return json.loads(row[0])

    def name(self, kind, ident):
        return self.get(kind,ident)['name'] if ident else '—'

    def authorize(self, actor, kind):
        row = self.db.execute('SELECT role FROM users WHERE name=?',(actor,)).fetchone()
        if not row or (row[0] != 'Admin' and kind not in ['builds','players','matches']):
            raise ValueError('Недостаточно прав')

    def add_user(self, name, password, role='Player', actor=None):
        if self.db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            self.authorize(actor,'users')
        elif role != 'Admin':
            raise ValueError('Первый пользователь должен быть Admin')
        if not name.strip() or len(password)<8 or role not in ['Admin','Player']:
            raise ValueError('Укажите имя, пароль от 8 символов и допустимую роль')
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),200000).hex()
        with self.db:
            self.db.execute('INSERT INTO users VALUES(?,?,?,?)',(name.strip(),salt,digest,role))

    def login(self, name, password):
        row = self.db.execute('SELECT salt,digest,role FROM users WHERE name=?',(name,)).fetchone()
        if row and hmac.compare_digest(row[1],hashlib.pbkdf2_hmac('sha256',password.encode(),row[0].encode(),200000).hex()):
            return row[2]
        raise ValueError('Неверный логин или пароль')

    def validate(self, kind, data):
        for key, caption, spec in SCHEMAS[kind]:
            value = data.get(key)
            if isinstance(spec,list):
                if value not in spec: raise ValueError(caption+': выберите значение')
            elif spec == 'int':
                if type(value) is not int or value<0: raise ValueError(caption+': нужно целое неотрицательное число')
            elif spec == 'bool':
                if type(value) is not bool: raise ValueError(caption+': нужно логическое значение')
            elif spec.startswith(('@','?')):
                if value or spec.startswith('@'): self.get(spec[1:],value)
            elif not isinstance(value,str): raise ValueError(caption+': нужна строка')
        if 'name' in data and not data['name'].strip(): raise ValueError('Введите название')
        for child in CHILDREN.get(kind,[]):
            if not isinstance(data.get(child,[]),list): raise ValueError('Ожидается таблица '+child)
            for row in data.get(child,[]): self.validate(child,row)
        if kind=='heroes' and not 1<=data['difficulty']<=3: raise ValueError('Сложность: 1–3')
        if kind=='roles' and not 1<=data['priority']<=9: raise ValueError('Приоритет: 1–9')
        if kind=='slots' and (not 1<=data['slot']<=6 or not 1<=data['order']<=99): raise ValueError('Слот: 1–6, порядок: 1–99')
        if kind=='builds':
            slots=[s['slot'] for s in data.get('slots',[])]
            if len(slots)!=len(set(slots)): raise ValueError('Номера слотов не должны повторяться')
        if kind=='matches':
            datetime.strptime(data['date'],'%Y-%m-%d %H:%M')
            if not 1<=data['duration']<=9999: raise ValueError('Длительность: 1–9999 минут')
            people = data.get('participants',[])
            ids = [p['player'] for p in people]
            if not people or len(ids)!=len(set(ids)): raise ValueError('Добавьте участников без повторения игроков')
            for p in people:
                if p.get('build') and self.get('builds',p['build'])['hero']!=p['hero']: raise ValueError('Сборка участника относится к другому герою')
            for p in data.get('purchases',[]):
                if p['player'] not in ids: raise ValueError('Покупатель отсутствует в участниках')
                if p['minute']>data['duration']: raise ValueError('Покупка позже окончания матча')

    def save(self, kind, data, actor):
        self.authorize(actor,kind)
        if kind not in ENTITIES: raise ValueError('Неизвестный справочник')
        data=copy.deepcopy(data)
        self.validate(kind,data)
        data.setdefault('id',secrets.token_hex(12))
        if kind=='matches':
            try: posted=self.get(kind,data['id']).get('posted',False)
            except ValueError: posted=False
            if posted: raise ValueError('Сначала отмените проведение матча')
            data['posted']=False
        # Keep references consistent when a build changes its hero.
        if kind=='builds':
            for m in self.all('matches'):
                for p in m['participants']:
                    if p.get('build')==data['id'] and p['hero']!=data['hero']:
                        raise ValueError('Сборка используется в матче с другим героем')
        with self.db: self._write(kind,data)
        return data['id']

    def _write(self,kind,data):
        self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(kind,data['id'],json.dumps(data,ensure_ascii=False)))

    def delete(self,kind,ident,actor):
        self.authorize(actor,kind)
        def contains(obj):
            if isinstance(obj,dict): return any(contains(v) for k,v in obj.items() if k!='id')
            if isinstance(obj,list): return any(contains(v) for v in obj)
            return obj==ident
        for other in ENTITIES:
            for r in self.all(other):
                if contains(r): raise ValueError('Запись используется: '+r['name'])
        if kind=='matches' and self.get(kind,ident).get('posted'): raise ValueError('Сначала отмените проведение')
        with self.db: self.db.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,ident))

    def post(self,ident,posted,actor):
        self.authorize(actor,'matches')
        data=self.get('matches',ident)
        self.validate('matches',data)
        data['posted']=bool(posted)
        with self.db: self._write('matches',data)

    def reports(self):
        stats=defaultdict(lambda:[0,0,0.0]); purchases=defaultdict(int)
        for match in self.all('matches'):
            if not match.get('posted'): continue
            heroes={p['player']:p['hero'] for p in match['participants']}
            for p in match['participants']:
                v=stats[(p['hero'],p['player'])]; v[0]+=1; v[1]+=int(match['win'])
                v[2]+=(p['kills']+p['assists'])/max(1,p['deaths'])
            for p in match['purchases']: purchases[(p['item'],heroes[p['player']],p['player'])]+=1
        winrate=[(self.name('heroes',h),self.name('players',p),v[0],v[1],round(v[1]/v[0]*100,2),round(v[2]/v[0],2)) for (h,p),v in stats.items()]
        popular=[(self.name('items',i),self.name('heroes',h),self.name('players',p),n) for (i,h,p),n in sorted(purchases.items(),key=lambda x:-x[1])]
        return winrate,popular

    def calculate(self,ident):
        build=self.get('builds',ident)
        items=[self.get('items',s['item']) for s in build.get('slots',[])]
        tips=[]
        if not any(i['category']=='Mobility' for i in items): tips.append('Не хватает мобильности')
        if not any(i['name'].lower() in ('bkb','black king bar') for i in items): tips.append('Нет BKB')
        if build['style']=='Крит' and not any(i['crit'] for i in items): tips.append('Нет предмета на крит')
        return sum(i['price'] for i in items),tips

    def export_data(self):
        return {'format':'FANDOTA2-1','records':{k:self.all(k) for k in ENTITIES}}

    def import_data(self,payload,actor):
        self.authorize(actor,'import')
        if payload.get('format')!='FANDOTA2-1': raise ValueError('Неверный формат файла')
        records=payload['records']
        # Atomic merge; validate after all references have been inserted.
        with self.db:
            for kind in ENTITIES:
                for data in records.get(kind,[]):
                    if not isinstance(data.get('id'),str) or not data['id']: raise ValueError('Нет ID')
                    if kind=='matches' and type(data.get('posted',False)) is not bool: raise ValueError('Неверный статус проведения')
                    self._write(kind,data)
            for kind in ENTITIES:
                for data in self.all(kind): self.validate(kind,data)

    def seed(self,actor):
        from demo import records
        self.authorize(actor,'seed')
        payload={'format':'FANDOTA2-1','records':{}}
        for kind,rows in records().items():
            known={r['name'] for r in self.all(kind)}
            ids={r['id'] for r in self.all(kind)}
            payload['records'][kind]=[r for r in rows if r['name'] not in known and r['id'] not in ids]
        self.import_data(payload,actor)
