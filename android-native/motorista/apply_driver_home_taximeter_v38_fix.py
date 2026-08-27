from pathlib import Path
import runpy

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')
old='startTaximeterUiPolling(taximeterSessionId,amount,meta);'
new='startTaximeterUiPolling(taximeterSessionId,amount,meta,running.optDouble("multiplier",1));'
if old not in text:
    raise SystemExit('Chamada do polling do taxímetro da home não encontrada')
text=text.replace(old,new,1)
path.write_text(text,encoding='utf-8')
print('Motorista v3.8: polling do taxímetro na home corrigido com multiplicador da sessão.')

runpy.run_path('apply_driver_vehicle_photos_v39.py',run_name='__main__')
