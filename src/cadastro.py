import re
import bcrypt

from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QMessageBox

from utils.cnn import conectar


class TelaCadastro(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        uic.loadUi("views/cadastro.ui", self)

        # Oculta os caracteres digitados nos campos de senha
        self.entry_senha.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password
        )

        self.entry_confirm.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password
        )

        # Conecta o botão à função de cadastro
        self.btn_cadastrar.clicked.connect(
            self.cadastrar_usuario
        )

    def validar_senha(self, senha):
        """
        Verifica se a senha atende aos requisitos mínimos.

        Requisitos:
        - No mínimo 8 caracteres
        - Pelo menos uma letra maiúscula
        - Pelo menos uma letra minúscula
        - Pelo menos 4 números
        - Pelo menos um caractere especial
        """

        if len(senha) < 8:
            return (
                False,
                "A senha deve ter no mínimo 8 caracteres."
            )

        if not re.search(r"[A-Z]", senha):
            return (
                False,
                "A senha deve conter pelo menos uma letra maiúscula."
            )

        if not re.search(r"[a-z]", senha):
            return (
                False,
                "A senha deve conter pelo menos uma letra minúscula."
            )

        quantidade_numeros = len(re.findall(r"\d", senha))

        if quantidade_numeros < 4:
            return (
                False,
                "A senha deve conter pelo menos 4 números."
            )

        if not re.search(r"[!@#$%&*_\-]", senha):
            return (
                False,
                "A senha deve conter pelo menos um caractere especial.\n"
                "Exemplos: ! @ # $ % & * _ -"
            )

        return True, ""

    def cadastrar_usuario(self):
        nome = self.entry_nome.text().strip()
        email = self.entry_email.text().strip().lower()
        senha = self.entry_senha.text()
        confirmar = self.entry_confirm.text()

        # Validação do nome
        if not nome:
            QMessageBox.warning(
                self,
                "Aviso",
                "Informe o nome."
            )
            self.entry_nome.setFocus()
            return

        # Validação do e-mail
        if not email:
            QMessageBox.warning(
                self,
                "Aviso",
                "Informe o e-mail."
            )
            self.entry_email.setFocus()
            return
        '''
        # Validação básica do formato do e-mail
        if not re.fullmatch(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):
            QMessageBox.warning(
                self,
                "E-mail inválido",
                "Informe um endereço de e-mail válido."
            )
            self.entry_email.setFocus()
            return

        # Verifica se a senha foi informada
        if not senha:
            QMessageBox.warning(
                self,
                "Aviso",
                "Informe a senha."
            )
            self.entry_senha.setFocus()
            return

        # Verifica os requisitos da senha
        senha_valida, mensagem = self.validar_senha(senha)

        if not senha_valida:
            QMessageBox.warning(
                self,
                "Senha fraca",
                mensagem
            )
            self.entry_senha.setFocus()
            return
        '''
        # Verifica se a confirmação foi informada
        if not confirmar:
            QMessageBox.warning(
                self,
                "Aviso",
                "Confirme a senha."
            )
            self.entry_confirm.setFocus()
            return

        # Verifica se as duas senhas são iguais
        if senha != confirmar:
            QMessageBox.warning(
                self,
                "Senhas diferentes",
                "A senha e a confirmação não coincidem."
            )

            self.entry_senha.clear()
            self.entry_confirm.clear()
            self.entry_senha.setFocus()
            return

        # As variáveis começam com None para evitar erro no finally
        conn = None
        cursor = None

        try:
            conn = conectar()
            cursor = conn.cursor()

            # Verifica se o e-mail já existe
            cursor.execute(
                """
                SELECT id_usuarios
                FROM usuarios
                WHERE email = %s
                """,
                (email,)
            )

            resultado = cursor.fetchone()

            if resultado:
                QMessageBox.warning(
                    self,
                    "E-mail já cadastrado",
                    "Este e-mail já está cadastrado."
                )
                self.entry_email.setFocus()
                return

            # Criptografa a senha com bcrypt
            senha_hash = bcrypt.hashpw(
                senha.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            # Insere o usuário no banco de dados
            cursor.execute(
                """
                INSERT INTO usuarios
                (
                    nome,
                    email,
                    senha
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    nome,
                    email,
                    senha_hash
                )
            )

            conn.commit()

            QMessageBox.information(
                self,
                "Sucesso",
                "Usuário cadastrado com sucesso!"
            )

            # Limpa os campos depois do cadastro
            self.entry_nome.clear()
            self.entry_email.clear()
            self.entry_senha.clear()
            self.entry_confirm.clear()

            self.entry_nome.setFocus()

        except Exception as erro:
            # Desfaz uma alteração incompleta no banco
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass

            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao cadastrar:\n{erro}"
            )

        finally:
            # Fecha o cursor apenas se ele tiver sido criado
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

            # Fecha a conexão apenas se ela tiver sido criada
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass