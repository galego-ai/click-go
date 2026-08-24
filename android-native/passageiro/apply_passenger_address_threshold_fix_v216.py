from pathlib import Path

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')
text=text.replace('if (safeQuery.length() < 2) {','if (safeQuery.length() < 3) {',1)
text=text.replace('if (query.length() < 2) return;','if (query.length() < 3) return;',1)
text=text.replace('if(query==null||query.trim().length()<2)return;','if(query==null||query.trim().length()<3)return;',1)
path.write_text(text,encoding='utf-8')
print('Autocomplete: sugestões rápidas a partir de 3 caracteres, compatível com geocode atual.')
