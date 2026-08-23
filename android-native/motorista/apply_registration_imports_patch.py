from pathlib import Path

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

if 'import java.util.ArrayList;' not in text:
    text=text.replace('import java.util.Arrays;\n','import java.util.ArrayList;\nimport java.util.Arrays;\n',1)
if 'import java.util.List;' not in text:
    text=text.replace('import java.util.Locale;\n','import java.util.Locale;\nimport java.util.List;\n',1)

path.write_text(text,encoding='utf-8')
print('Imports do cadastro nativo do motorista validados.')
