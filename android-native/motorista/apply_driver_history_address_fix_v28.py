from pathlib import Path
p=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=p.read_text(encoding='utf-8')
old='''return s.matches("^-?\\\\d{1,3}[.,]\\\\d{3,}\\\\s*[,;/]\\\\s*-?\\\\d{1,3}[.,]\\\\d{3,}$")||s.contains("latitude")||s.contains("longitude");'''
new='''return s.matches("^-?\\\\d{1,3}[.,]\\\\d{3,}\\\\s*[,;/]\\\\s*-?\\\\d{1,3}[.,]\\\\d{3,}$")||s.contains("latitude")||s.contains("longitude")||s.contains("marcado no mapa")||s.contains("marcada no mapa")||s.equals("minha localização atual")||s.equals("minha localizacao atual");'''
if old not in text: raise SystemExit('coordinateLike não encontrado')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('Histórico do motorista: placeholders de mapa passam por reverse geocoding.')
