"""Учебные данные: цены и характеристики не привязаны к текущему патчу."""
def records():
    heroes=[]
    groups=[('Сила','Sven,Axe,Tidehunter,Earthshaker,Pudge,Tiny,Dragon Knight'),('Ловкость','Phantom Assassin,Weaver,Anti-Mage,Juggernaut,Drow Ranger,Luna,Slark'),('Интеллект','Crystal Maiden,Lina,Lion,Zeus,Shadow Shaman,Puck'),('Универсал','Windranger,Mirana,Invoker,Venomancer,Dark Willow')]
    for attribute,names in groups:
        for name in names.split(','):
            heroes.append(dict(id='hero-'+name,name=name,attribute=attribute,difficulty=2,description='Учебная карточка. Характеристики уточняются вручную.',hp=0,speed=0,active=True,roles=[dict(role='Carry' if attribute=='Ловкость' else 'Offlane' if attribute=='Сила' else 'SoftSupport',priority=1)]))
    specs=[('Power Treads','Boots',1400,False,True,False,True),('Phase Boots','Boots',1500,False,True,False,True),('Blink Dagger','Mobility',2250,False,False,False,True),('Black King Bar','Survivability',4050,False,False,True,True),('Daedalus','CritDPS',5100,True,False,False,False),('Butterfly','AttackSpeed',5450,False,True,True,False),('Heart of Tarrasque','Survivability',5200,False,False,True,False),('Force Staff','Mobility',2200,False,False,True,True),('Glimmer Cape','Utility',2150,False,False,True,True),('Battle Fury','Farming',4100,False,False,False,False),('Assault Cuirass','Aura',5125,False,True,True,False),('Moon Shard','AttackSpeed',4000,False,True,False,True)]
    items=[dict(id='item-'+n,name=n,category=c,price=p,description='Условная учебная цена; отредактируйте для своего патча.',crit=cr,speed=s,survival=sv,ability=a) for n,c,p,cr,s,sv,a in specs]
    builds=[]
    sets=[('PA Crit','Phantom Assassin','Крит',['Power Treads','Battle Fury','Black King Bar','Daedalus','Butterfly','Blink Dagger']),('Axe Tank','Axe','Живучесть',['Phase Boots','Blink Dagger','Black King Bar','Heart of Tarrasque','Assault Cuirass','Force Staff']),('Weaver Speed','Weaver','Скорость',['Power Treads','Butterfly','Moon Shard','Black King Bar','Daedalus','Assault Cuirass'])]
    for name,hero,style,names in sets:
        builds.append(dict(id='build-'+name,name=name,hero='hero-'+hero,style=style,role='Offlane' if hero=='Axe' else 'Carry',description='Учебный пример для проверки приложения, не игровая рекомендация.',situation='Демонстрация',slots=[dict(slot=i,item='item-'+n,order=i,required=True,comment='') for i,n in enumerate(names,1)]))
    return dict(heroes=heroes,items=items,builds=builds,players=[dict(id='player-me',name='Я',role='Carry',style='Крит',comment='')],matches=[])
