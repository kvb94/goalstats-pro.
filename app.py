import os, math, datetime as dt
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title='GoalStats Pro',page_icon='⚽',layout='wide')
st.title('⚽ GoalStats Pro')
st.caption('Partidos reales · Historial de goles · Probabilidades estimadas (modelo Poisson)')
API_KEY = st.secrets.get('API_FOOTBALL_KEY', os.getenv('API_FOOTBALL_KEY',''))
LEAGUES={'Premier League':39,'LaLiga':140,'Serie A':135,'Bundesliga':78,'Ligue 1':61,'Champions League':2,'Primeira Liga':94,'Eredivisie':88,'Süper Lig':203,'Brasileirão':71,'MLS':253}
BASE='https://v3.football.api-sports.io'
@st.cache_data(ttl=1800,show_spinner=False)
def api(path,params,key):
    r=requests.get(BASE+path,headers={'x-apisports-key':key},params=params,timeout=20)
    r.raise_for_status()
    body=r.json()
    if body.get('errors'): raise RuntimeError(str(body['errors']))
    return body.get('response',[])

def season_for(date, league):
    if league in ('Brasileirão','MLS'): return date.year
    return date.year if date.month>=7 else date.year-1

def poisson(lam,k): return math.exp(-lam)*lam**k/math.factorial(k)
def matrix(lh,la,cap=18): return [(h,a,poisson(lh,h)*poisson(la,a)) for h in range(cap+1) for a in range(cap+1)]
def pct(v): return f'{v*100:.1f}%'
def historical(team_id,league_id,season,key):
    fixtures=api('/fixtures',{'team':team_id,'league':league_id,'season':season,'status':'FT'},key)
    fixtures.sort(key=lambda x:x['fixture']['date'],reverse=True)
    records=[]
    for f in fixtures:
        g=f.get('goals',{}); h=g.get('home'); a=g.get('away')
        if h is None or a is None:continue
        home=f['teams']['home']['id']==team_id
        records.append({'date':f['fixture']['date'][:10], 'venue':'Local' if home else 'Visitante','gf':h if home else a,'ga':a if home else h,'total':h+a})
    return pd.DataFrame(records)

if not API_KEY:
    st.warning('Conecta una clave de API-Football para mostrar partidos reales. Añade API_FOOTBALL_KEY en Streamlit Secrets o como variable de entorno.')
    st.info('Documentación y registro: https://www.api-football.com/')
    st.stop()
league=st.selectbox('Liga',list(LEAGUES))
date=st.date_input('Fecha del partido',dt.date.today())
season=season_for(date,league)
try:
    games=api('/fixtures',{'league':LEAGUES[league],'season':season,'date':date.isoformat()},API_KEY)
except Exception as e:
    st.error(f'Error consultando partidos: {e}');st.stop()
if not games:
    st.info('No hay partidos disponibles para esta liga y fecha, o el proveedor no los incluye en tu plan.')
    st.stop()
choices={f"{g['teams']['home']['name']} vs {g['teams']['away']['name']} · {g['fixture']['date'][11:16]} UTC":g for g in games}
game=choices[st.selectbox('Partido',list(choices))]
home=game['teams']['home'];away=game['teams']['away']
st.subheader(f"{home['name']} vs {away['name']}")
st.caption('Los cálculos usan únicamente encuentros finalizados antes del inicio del partido seleccionado. Se excluyen partidos posteriores para evitar fuga de información.')
try:
    dh=historical(home['id'],LEAGUES[league],season,API_KEY)
    da=historical(away['id'],LEAGUES[league],season,API_KEY)
    cutoff=game['fixture']['date'][:10]
    dh=dh[dh.date<cutoff];da=da[da.date<cutoff]
except Exception as e:
    st.error(f'No se pudo recuperar el historial: {e}');st.stop()
n=st.slider('Últimos partidos por equipo',5,20,10)
h=dh.head(n);a=da.head(n)
if len(h)<5 or len(a)<5:
    st.warning('Historial insuficiente para una estimación razonable (mínimo cinco partidos previos por equipo).')
    st.stop()
hhome=h[h.venue=='Local'];aaway=a[a.venue=='Visitante']
if len(hhome)<3 or len(aaway)<3:
    st.warning('Pocos encuentros local/visitante: se utilizan promedios generales de cada equipo.')
    hhome=h;aaway=a
lh=max(.05,(hhome.gf.mean()+aaway.ga.mean())/2)
la=max(.05,(aaway.gf.mean()+hhome.ga.mean())/2)
st.markdown('### Historial de goles')
c1,c2=st.columns(2)
for col,name,df in [(c1,home['name'],h),(c2,away['name'],a)]:
    with col:
        st.markdown(f'**{name}** · {len(df)} partidos')
        st.metric('Goles anotados / partido',f'{df.gf.mean():.2f}')
        st.metric('Goles recibidos / partido',f'{df.ga.mean():.2f}')
        st.metric('Over 1.5 histórico',pct((df.total>=2).mean()))
        st.metric('Over 2.5 histórico',pct((df.total>=3).mean()))
        st.metric('Ambos marcan histórico',pct(((df.gf>0)&(df.ga>0)).mean()))
        st.dataframe(df,hide_index=True,use_container_width=True)
st.markdown('### Probabilidades de goles · estimación')
st.caption(f'Goles esperados aproximados: {home["name"]} {lh:.2f} · {away["name"]} {la:.2f}. Modelo Poisson independiente, sin calibración; no equivale a probabilidades garantizadas.')
M=matrix(lh,la)
rows=[]
for threshold in range(6):
    over=sum(p for x,y,p in M if x+y>threshold)
    rows.append({'Mercado':f'Over {threshold}.5','Probabilidad':pct(over),'Under':pct(1-over)})
st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
btts=sum(p for x,y,p in M if x>0 and y>0)
st.metric('Ambos equipos marcan',pct(btts))
st.markdown('### Mercados por equipo')
for name,lam in [(home['name'],lh),(away['name'],la)]:
    st.write(name, ' · '.join(f'Over {k}.5: {pct(1-sum(poisson(lam,i) for i in range(k+1)))}' for k in range(4)))
st.markdown('### Marcadores más probables')
st.dataframe(pd.DataFrame([{'Marcador':f'{x}-{y}','Probabilidad':pct(p)} for x,y,p in sorted(M,key=lambda t:t[2],reverse=True)[:12]]),hide_index=True,use_container_width=True)
st.markdown('### Analizador de combinaciones')
min_total=st.number_input('Mínimo de goles totales (incluido)',0,10,2)
max_total=st.number_input('Máximo de goles totales (incluido)',0,12,4)
min_home=st.number_input('Mínimo goles local',0,10,0)
max_home=st.number_input('Máximo goles local',0,12,10)
min_away=st.number_input('Mínimo goles visitante',0,10,0)
max_away=st.number_input('Máximo goles visitante',0,12,10)
both=st.checkbox('Ambos equipos marcan')
valid=[(x,y,p) for x,y,p in M if min_total<=x+y<=max_total and min_home<=x<=max_home and min_away<=y<=max_away and (not both or (x>0 and y>0))]
st.metric('Probabilidad conjunta estimada',pct(sum(p for _,_,p in valid)))
st.dataframe(pd.DataFrame([{'Marcador':f'{x}-{y}','Probabilidad':pct(p)} for x,y,p in sorted(valid,key=lambda t:t[2],reverse=True)[:30]]),hide_index=True,use_container_width=True)
st.caption('Aviso: no son recomendaciones de apuestas. La independencia de goles, el tamaño de muestra y la ausencia de ajustes por lesiones, alineaciones y fuerza del calendario limitan la precisión. No se garantiza ningún resultado.')
