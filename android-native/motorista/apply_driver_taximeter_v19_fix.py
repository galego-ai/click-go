from pathlib import Path

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

text=text.replace(
    'startTaximeterUiPolling(taximeterSessionId,amount,meta);',
    'startTaximeterUiPolling(taximeterSessionId,amount,meta,session.optDouble("multiplier",1));',
    1
)
text=text.replace(
    'private void startTaximeterUiPolling(String sessionId,TextView amount,TextView meta){',
    'private void startTaximeterUiPolling(String sessionId,TextView amount,TextView meta,double multiplier){',
    1
)
text=text.replace(
    'taximeterMeta(r.optDouble("distance_m",0),r.optInt("elapsed_seconds",0),1)',
    'taximeterMeta(r.optDouble("distance_m",0),r.optInt("elapsed_seconds",0),multiplier)',
    1
)

path.write_text(text,encoding='utf-8')
print('Taxímetro v1.9: multiplicador mantido nas atualizações ao vivo.')
