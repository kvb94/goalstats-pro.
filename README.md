# GoalStats Pro

Aplicación Streamlit para consultar partidos reales y estadísticas históricas con API-Football, y calcular probabilidades estimadas de goles.

## Inicio

1. Registra una cuenta en https://www.api-football.com/ y consigue tu API key.
2. Instala Python 3.10+ y ejecuta `pip install -r requirements.txt`.
3. Configura `API_FOOTBALL_KEY` como variable de entorno, o en `.streamlit/secrets.toml` con `API_FOOTBALL_KEY = "TU_CLAVE"`.
4. Ejecuta `streamlit run app.py`.
5. Abre la URL local que muestra Streamlit. Para usarla desde iPhone fuera de tu red, despliega la aplicación en un servidor o Streamlit Community Cloud y configura la clave en Secrets.

## Limitaciones de la v1

- La cobertura de ligas, partidos e históricos depende del proveedor y del plan contratado.
- La temporada se infiere según el calendario habitual; algunas competiciones pueden necesitar ajuste manual.
- Solo se emplean partidos de liga de la temporada seleccionada y previos a la fecha del encuentro; no se mezclan otras competiciones.
- Las probabilidades se calculan con una aproximación Poisson independiente y medias recientes; no incluyen xG real, lesiones ni calibración retrospectiva.
- Los horarios en el selector se indican en UTC.
