from pathlib import Path
import re

root = Path('app')
main_path = root / 'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path = root / 'src/main/java/com/clickgo/motorista/DriverRepository.java'

text = main_path.read_text(encoding='utf-8')
repo = repo_path.read_text(encoding='utf-8')

# v3.5: o login não deve revelar se um e-mail possui ou não uma conta de motorista.
# Mantemos a autenticação normal e exibimos a mesma resposta para credencial inválida.
old_login_probe = 'shown = DriverRepository.driverAccountExists(email) ? "Senha incorreta." : "Esse usuário não existe.";'
if old_login_probe not in text:
    raise SystemExit('Consulta de existência da conta não encontrada no login final')
text = text.replace(old_login_probe, 'shown = "E-mail ou senha incorretos.";', 1)

# Recuperação também deve ser neutra. O endpoint de recuperação pode receber o e-mail,
# mas o aplicativo não faz uma consulta separada para confirmar se a conta existe.
recover_pattern = re.compile(
    r'''    private void recover\(String email\) \{.*?\n    \}\n\n(?=    private void login\(String email, String password\))''',
    re.S,
)
recover_replacement = '''    private void recover(String email) {\n        if(email.isBlank()){toast("Informe seu e-mail.");return;}\n        io.execute(() -> {\n            try {\n                JSONObject body = new JSONObject().put("email",email);\n                ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha%3Fdestino%3Dmotorista-app",body);\n                ui.post(() -> new android.app.AlertDialog.Builder(this)\n                        .setTitle("Recuperação de senha")\n                        .setMessage("Se este e-mail estiver cadastrado, você receberá um link para criar uma nova senha.")\n                        .setPositiveButton("Voltar ao login",(d,w)->showLogin())\n                        .show());\n            } catch(Exception e){ui.post(()->toast(msg(e)));}\n        });\n    }\n\n'''
text, count = recover_pattern.subn(recover_replacement, text, count=1)
if count != 1:
    raise SystemExit('Método recover final não encontrado')

# Remove do cliente o RPC que consultava auth.users por e-mail.
account_method_pattern = re.compile(
    r'''\n    public static boolean driverAccountExists\(String email\) throws Exception \{.*?\n    \}\n\n(?=    public static JSONObject signUp\(JSONObject body\) throws Exception \{)''',
    re.S,
)
repo, count = account_method_pattern.subn('\n', repo, count=1)
if count != 1:
    raise SystemExit('Método driverAccountExists não encontrado no DriverRepository final')

if 'driverAccountExists' in text or 'driverAccountExists' in repo:
    raise SystemExit('Referência residual a driverAccountExists após patch de privacidade')
if 'E-mail ou senha incorretos.' not in text:
    raise SystemExit('Mensagem neutra de login não aplicada')
if 'Se este e-mail estiver cadastrado' not in text:
    raise SystemExit('Mensagem neutra de recuperação não aplicada')

main_path.write_text(text, encoding='utf-8')
repo_path.write_text(repo, encoding='utf-8')
print('Driver v3.5 privacy patch applied')
