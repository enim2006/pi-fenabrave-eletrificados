"""Tratamento dos CSVs Fenabrave (02_dados_extraidos) para o dashboard do PI — Grupo 08.
Uso:  from tratamento_fenabrave import carregar;  D = carregar('02_dados_extraidos');  D['marca'], D['modelo'], D['resumo'], D['log']
Corrige falhas do parser de PDF: rankings de segmentos trocados/colados, meses ausentes e quantidades corrompidas.
Estimativas ficam marcadas na coluna `estimado` (marca/modelo) e listadas em D['log']."""
import pandas as pd, numpy as np
LOG=[]
def clean_marca(mar,res):
    """fato_marca: o parser mistura 3 rankings lado a lado do PDF (Autos, Com. Leves, Autos+Com. Leves).
    Reclassifica Autos/Com. Leves pelo total implícito (qtd ÷ share) comparado aos totais do resumo;
    descarta o ranking combinado; recalcula a quantidade quando ela não bate com o share."""
    T=res[res.segmento.isin(['Autos','Com. Leves','Autos + Com. Leves'])].pivot_table(index=['ano','mes_num'],columns='segmento',values='quantidade_mes')
    T['Autos + Com. Leves']=T['Autos + Com. Leves'].fillna(T['Autos']+T['Com. Leves'])
    m=mar.copy(); m['seg_orig']=m.segmento; m['qtd_orig']=m.quantidade_mes
    lv=m.segmento.isin(['Autos','Com. Leves'])
    x=m[lv].join(T,on=['ano','mes_num'])
    imp=x.quantidade_mes/x.participacao_pct*100
    cands=['Autos','Com. Leves','Autos + Com. Leves']
    err=pd.concat({c:(imp/x[c]-1).abs() for c in cands},axis=1)
    best=err.idxmin(axis=1); besterr=err.min(axis=1)
    tol=np.where(x.participacao_pct>=1,0.03,0.25)
    ok=besterr<=tol
    newseg=np.where(ok,best,x.segmento)
    m.loc[lv,'segmento']=newseg
    # quantidade inconsistente com o share (linha fundida pelo parser): recalcula pelo share
    bad=(~ok)&(x.participacao_pct>=1)
    tot_lab=pd.Series([x.loc[i,s] for i,s in zip(x.index,x.segmento)],index=x.index)
    m.loc[bad[bad].index,'quantidade_mes']=(x.participacao_pct*tot_lab/100).round()[bad]
    LOG.append(f"fato_marca: {int((newseg!=x.segmento.values).sum())} linhas reclassificadas; {int(bad.sum())} quantidades recalculadas pelo share")
    # recupera marcas de Autos que o parser perdeu: Autos = (Autos+Com. Leves) − Com. Leves
    comb=m[m.segmento=='Autos + Com. Leves'].drop_duplicates(['ano','mes_num','fabricante']).set_index(['ano','mes_num','fabricante']).quantidade_mes
    cl=m[m.segmento=='Com. Leves'].drop_duplicates(['ano','mes_num','fabricante']).set_index(['ano','mes_num','fabricante']).quantidade_mes
    au=m[m.segmento=='Autos'].drop_duplicates(['ano','mes_num','fabricante']).set_index(['ano','mes_num','fabricante']).quantidade_mes
    miss=comb.index.difference(au.index)
    rec=(comb.loc[miss]-cl.reindex(miss).fillna(0)).clip(lower=0)
    rec=rec[rec>0]
    if len(rec):
        add=rec.reset_index().rename(columns={'quantidade_mes':'quantidade_mes'})
        add['segmento']='Autos'; add['tipo_venda']='Total'; add['rank']=np.nan; add['recuperado']=True
        add=add.merge(m[['ano','mes_num','mes_nome','data']].drop_duplicates(['ano','mes_num']),on=['ano','mes_num'])
        add=add.join(T['Autos'],on=['ano','mes_num']); add['participacao_pct']=(add.quantidade_mes/add['Autos']*100).round(2); add=add.drop(columns='Autos')
        m=pd.concat([m,add],ignore_index=True)
    LOG.append(f"fato_marca: {len(rec)} marca-mês de Autos recuperados como (Autos+Com. Leves) − Com. Leves")
    m=m[m.segmento!='Autos + Com. Leves']
    n0=len(m); m=m.drop_duplicates(['ano','mes_num','segmento','fabricante']); LOG.append(f"fato_marca: {n0-len(m)} duplicatas removidas")
    return m
def clean_modelo(mod):
    """fato_modelo: em 2022-01/02/04/10 o ranking Total de Com. Leves saiu rotulado como Autos."""
    k=['ano','mes_num','segmento','tipo_venda','rank']
    mo=mod.copy()
    dupm=set(map(tuple,mo[mo.duplicated(k,keep=False)][['ano','mes_num']].drop_duplicates().values))
    key=mo[['ano','mes_num']].apply(tuple,axis=1)
    ref=mo[~key.isin(dupm)].groupby('modelo').segmento.agg(lambda s:s.mode()[0])
    sel=key.isin(dupm)&(mo.segmento=='Autos')&(mo.tipo_venda=='Total')&(mo.modelo.map(ref)=='Com. Leves')
    mo.loc[sel,'segmento']='Com. Leves'
    LOG.append(f"fato_modelo: {int(sel.sum())} linhas de Com. Leves que estavam rotuladas como Autos")
    n0=len(mo); mo=mo.drop_duplicates(['ano','mes_num','segmento','tipo_venda','modelo']); LOG.append(f"fato_modelo: {n0-len(mo)} duplicatas removidas")
    return mo

def impute_marca_autos(mar,mod,idx,tops=40):
    """Marca-mês de Autos ausente no ranking de marcas: estima pela soma dos modelos da marca (fato_modelo, Total)
    × razão marca/modelos da própria marca nos meses vizinhos (±3)."""
    a=mar[mar.segmento=='Autos']
    M=a.pivot_table(index='data',columns='fabricante',values='quantidade_mes',aggfunc='sum').reindex(idx)
    mm=mod[(mod.segmento=='Autos')&(mod.tipo_venda=='Total')].copy()
    mm['fabricante']=mm.modelo.str.split('/').str[0].str.strip().str.upper()
    S=mm.pivot_table(index='data',columns='fabricante',values='quantidade_mes',aggfunc='sum').reindex(idx)
    brands=a.groupby('fabricante').quantidade_mes.sum().sort_values(ascending=False).head(tops).index
    rows=[]
    for b in brands:
        if b not in S: continue
        ratio=(M[b]/S[b]).replace([np.inf,-np.inf],np.nan)
        for d in M.index[M[b].isna()&S[b].notna()]:
            # só imputa se a marca está presente nos meses vizinhos (evita inventar marcas que não existiam)
            win=ratio.loc[d-pd.DateOffset(months=3):d+pd.DateOffset(months=3)].dropna()
            if len(win)>=2:
                rows.append(dict(ano=d.year,mes_num=d.month,data=d,segmento='Autos',tipo_venda='Total',fabricante=b,
                                 quantidade_mes=round(S.loc[d,b]*win.median()),estimado=True))
    LOG.append(f"fato_marca: {len(rows)} marca-mês de Autos estimados pela soma de modelos (ex.: jan/2022 inteiro, GM em jan e mai/2024)")
    return pd.concat([mar,pd.DataFrame(rows)],ignore_index=True) if rows else mar

def impute_modelo_total(mod):
    """Meses sem ranking Total em fato_modelo (ex.: jan/2024, só Varejo): Total ≈ Varejo × razão Total/Varejo do modelo nos meses vizinhos."""
    mo=mod.copy(); mo['data']=pd.to_datetime(dict(year=mo.ano,month=mo.mes_num,day=1))
    rows=[]
    for seg in ['Autos','Com. Leves']:
        s=mo[mo.segmento==seg]
        T=s[s.tipo_venda=='Total'].pivot_table(index='data',columns='modelo',values='quantidade_mes',aggfunc='sum')
        V=s[s.tipo_venda=='Varejo'].pivot_table(index='data',columns='modelo',values='quantidade_mes',aggfunc='sum')
        for d in sorted(set(V.index)-set(T.index)):
            R=(T/V.reindex(T.index)).loc[d-pd.DateOffset(months=3):d+pd.DateOffset(months=3)]
            for mdl,v in V.loc[d].dropna().items():
                r=R[mdl].dropna() if mdl in R else pd.Series(dtype=float)
                if len(r)>=2:
                    rows.append(dict(ano=d.year,mes_num=d.month,data=d,segmento=seg,tipo_venda='Total',modelo=mdl,quantidade_mes=round(v*r.median()),estimado=True))
    LOG.append(f"fato_modelo: {len(rows)} modelo-mês Total estimados a partir do Varejo (meses sem ranking Total: jan/2024)")
    out=pd.concat([mo,pd.DataFrame(rows)],ignore_index=True) if rows else mo
    return out.drop(columns='data')

# Valores lidos diretamente na página "Ranking por marca" do PDF, para marca-mês que o parser
# perdeu ou leu errado. Prevalecem sobre estimativas (estimado=False). Em 2024_01 a fonte do PDF
# tem mapa de caracteres deslocado: (cid:N) corresponde ao caractere N+29.
MARCA_CONFERIDA_PDF = {
    # (ano, mes, segmento, fabricante): (quantidade, participacao_pct)
    (2024, 1, 'Autos', 'GM'): (15063, 12.71),
    (2024, 1, 'Autos', 'CAOA CHERY'): (3470, 2.93),
    (2024, 1, 'Com. Leves', 'PEUGEOT'): (202, 0.60),
    (2024, 1, 'Com. Leves', 'IVECO'): (177, 0.53),
    (2024, 1, 'Com. Leves', 'M.BENZ'): (99, 0.30),
    (2024, 1, 'Com. Leves', 'JAC'): (10, 0.03),
    (2024, 5, 'Autos', 'GM'): (21116, 14.66),
}

def aplicar_marca_conferida(mar):
    m=mar.copy()
    n=0
    for (a,mes,seg,fab),(q,p) in MARCA_CONFERIDA_PDF.items():
        msk=(m.ano==a)&(m.mes_num==mes)&(m.segmento==seg)&(m.fabricante==fab)
        if msk.any():
            m.loc[msk,['quantidade_mes','participacao_pct','estimado']]=[q,p,False]
        else:
            m=pd.concat([m,pd.DataFrame([dict(ano=a,mes_num=mes,data=pd.Timestamp(a,mes,1),segmento=seg,tipo_venda='Total',
                                               fabricante=fab,quantidade_mes=q,participacao_pct=p,estimado=False)])],ignore_index=True)
        n+=1
    LOG.append(f"fato_marca: {n} marca-mês substituídos por valores conferidos no PDF (jan e mai/2024)")
    return m

# fato_eletrificados_resumo: segmento-mês ausentes na extração, lidos nas páginas
# "Mercado de Eletrificados" dos PDFs 2024_01 (Com. Leves) e 2024_04 (Caminhões, Ônibus).
ELR_CONFERIDO_PDF = {
    # (ano, mes, segmento): {tipo: quantidade}
    (2024, 1, 'Com. Leves'): {'Híbridos': 26, 'Elétricos': 23, 'Total Eletrificados': 49},
    (2024, 4, 'Caminhões'): {'Híbridos': 0, 'Elétricos': 31, 'Total Eletrificados': 31},
    (2024, 4, 'Ônibus'): {'Híbridos': 0},
}

def aplicar_elr_conferido(elr):
    rows=[]
    for (a,mes,seg),tipos in ELR_CONFERIDO_PDF.items():
        for tipo,q in tipos.items():
            if not ((elr.ano==a)&(elr.mes_num==mes)&(elr.segmento==seg)&(elr.tipo_eletrificacao==tipo)).any():
                rows.append(dict(ano=a,mes_num=mes,segmento=seg,tipo_eletrificacao=tipo,quantidade_mes=q,data=pd.Timestamp(a,mes,1)))
    LOG.append(f"fato_eletrificados_resumo: {len(rows)} segmento-mês incluídos a partir do PDF (jan e abr/2024)")
    return pd.concat([elr,pd.DataFrame(rows)],ignore_index=True) if rows else elr

def _fix_res(res):
    """Completa segmentos ausentes do resumo pelas identidades publicadas no próprio informativo."""
    P=res.pivot_table(index='data',columns='segmento',values='quantidade_mes',aggfunc='sum')
    ids=[('Autos',lambda r:r['Autos + Com. Leves']-r['Com. Leves']),('Com. Leves',lambda r:r['Autos + Com. Leves']-r['Autos']),
         ('Caminhões',lambda r:r['Caminhões + Ônibus']-r['Ônibus']),('Ônibus',lambda r:r['Caminhões + Ônibus']-r['Caminhões']),
         ('Autos',lambda r:r['Subtotal (A a D)']-r['Com. Leves']-r['Caminhões']-r['Ônibus']),
         ('Com. Leves',lambda r:r['Subtotal (A a D)']-r['Autos']-r['Caminhões']-r['Ônibus']),
         ('Caminhões',lambda r:r['Subtotal (A a D)']-r['Autos']-r['Com. Leves']-r['Ônibus']),
         ('Autos + Com. Leves',lambda r:r['Autos']+r['Com. Leves']),('Caminhões + Ônibus',lambda r:r['Caminhões']+r['Ônibus'])]
    added=[]
    for _ in range(3):
        for seg,f in ids:
            for d in P.index[P[seg].isna()]:
                v=f(P.loc[d])
                if pd.notna(v): P.loc[d,seg]=v; added.append((d.strftime('%Y-%m'),seg,int(v)))
    rows=[dict(ano=int(d[:4]),mes_num=int(d[5:]),segmento=s,quantidade_mes=v,data=pd.Timestamp(d+'-01')) for d,s,v in added]
    return pd.concat([res,pd.DataFrame(rows)],ignore_index=True), added

def _calib_modelo(mod,tot,idx,SEG=('Autos','Com. Leves')):
    mod=mod.copy()
    if 'estimado' not in mod: mod['estimado']=False
    mod['estimado']=mod['estimado'].astype('boolean').fillna(False).astype(bool)
    rows=[]
    for seg in SEG:
        T=mod[(mod.segmento==seg)&(mod.tipo_venda=='Total')].pivot_table(index='data',columns='modelo',values='quantidade_mes',aggfunc='sum').reindex(idx)
        for d in T.index[T.isna().all(axis=1)]:           # mês sem nenhum dado: média dos vizinhos por modelo
            p,n=d-pd.DateOffset(months=1),d+pd.DateOffset(months=1)
            if p in T.index and n in T.index:
                v=T.loc[[p,n]].mean().dropna()
                for mdl,q in v.items(): rows.append(dict(ano=d.year,mes_num=d.month,data=d,segmento=seg,tipo_venda='Total',modelo=mdl,quantidade_mes=q,estimado=True))
    if rows:
        LOG.append(f"fato_modelo: {len(rows)} modelo-mês Total estimados pela média dos meses vizinhos (abr/2024 vazio na base)")
        mod=pd.concat([mod,pd.DataFrame(rows)],ignore_index=True)
    # calibra: soma estimada do mês = total do segmento × cobertura mediana dos vizinhos (±3 meses)
    tv=mod[mod.tipo_venda=='Total']
    for seg in SEG:
        s=tv[tv.segmento==seg]; cov=(s[~s.estimado].groupby('data').quantidade_mes.sum()/tot[seg]).dropna()
        for d in s[s.estimado].data.unique():
            c=cov.loc[d-pd.DateOffset(months=3):d+pd.DateOffset(months=3)].median()
            if pd.isna(tot[seg].get(d)): continue
            msk=(mod.tipo_venda=='Total')&(mod.segmento==seg)&(mod.data==d)&mod.estimado
            f=tot[seg][d]*c/mod.loc[msk,'quantidade_mes'].sum(); mod.loc[msk,'quantidade_mes']=(mod.loc[msk,'quantidade_mes']*f).round()
    return mod

def carregar(pasta):
    import os
    def rd(n):
        d=pd.read_csv(os.path.join(pasta,n+'.csv')); d['data']=pd.to_datetime(dict(year=d.ano,month=d.mes_num,day=1)); return d
    LOG.clear()
    res=rd('fato_resumo_segmento'); mar=rd('fato_marca'); mod=rd('fato_modelo'); mot=rd('fato_motorizacao')
    elr=aplicar_elr_conferido(rd('fato_eletrificados_resumo'))
    res,fix=_fix_res(res); LOG.extend([f"fato_resumo_segmento: {s} {d} = {v} (identidade do informativo)" for d,s,v in fix])
    ms=mot.groupby(['data','segmento']).quantidade_mes.sum()
    P=res.pivot_table(index='data',columns='segmento',values='quantidade_mes',aggfunc='sum')
    for s in ['Autos','Com. Leves']:
        for d in P.index[P[s].isna()]:
            if (d,s) in ms.index:
                res=pd.concat([res,pd.DataFrame([dict(ano=d.year,mes_num=d.month,segmento=s,quantidade_mes=int(ms[(d,s)]),data=d)])],ignore_index=True)
                LOG.append(f"fato_resumo_segmento: {s} {d:%Y-%m} = soma de fato_motorizacao")
    idx=pd.date_range(res.data.min(),res.data.max(),freq='MS')
    tot=res[res.segmento.isin(['Autos','Com. Leves'])].pivot_table(index='data',columns='segmento',values='quantidade_mes',aggfunc='sum').reindex(idx)
    norm=lambda s:s.astype(str).str.strip().str.upper().str.rstrip('.').str.strip()
    mar['fabricante']=norm(mar.fabricante)
    mar=clean_marca(mar,res)
    mod=clean_modelo(mod); mod=impute_modelo_total(mod); mod['data']=pd.to_datetime(dict(year=mod.ano,month=mod.mes_num,day=1))
    mod=_calib_modelo(mod,tot,idx)
    mar=impute_marca_autos(mar,mod,idx)
    for d in (mar,mod):
        d['estimado']=d.get('estimado',False); d['estimado']=d['estimado'].astype('boolean').fillna(False).astype(bool)
    mar=aplicar_marca_conferida(mar)
    return dict(resumo=res,marca=mar,modelo=mod,eletrificados_resumo=elr,motorizacao=mot,log=list(LOG))
