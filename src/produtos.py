from decimal import Decimal, InvalidOperation

from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QMessageBox, QAbstractItemView

from utils.cnn import conectar


class GerenciadorProdutos:
    """Controla o cadastro, a edição, a listagem e a exclusão de produtos."""

    def __init__(self, tela):
        self.tela = tela

        # Modelo utilizado pela tabela de produtos
        self.modelo = QStandardItemModel()

        self.modelo.setHorizontalHeaderLabels(
            [
                "Código",
                "Nome",
                "Descrição",
                "Categoria",
                "Preço",
                "Estoque",
            ]
        )

        self.tela.tableView_2.setModel(self.modelo)

        # Configura a seleção por linha
        self.tela.tableView_2.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.tela.tableView_2.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # Impede que o usuário edite diretamente os dados da tabela
        self.tela.tableView_2.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        # Conecta os botões aos respectivos métodos
        self.tela.btn_salvar_2.clicked.connect(
            self.salvar_produto
        )

        self.tela.btn_limpar_2.clicked.connect(
            self.limpar_campos
        )

        self.tela.btn_excluir_2.clicked.connect(
            self.excluir_produto
        )

        # Carrega os dados do produto ao dar duplo clique
        self.tela.tableView_2.doubleClicked.connect(
            self.carregar_campos_ao_duplo_clique
        )

        # Carrega os produtos cadastrados ao iniciar
        self.carregar_dados_na_tabela()

    def carregar_dados_na_tabela(self):
        """Carrega os produtos cadastrados no banco de dados."""

        # Remove os dados atuais da tabela
        self.modelo.removeRows(
            0,
            self.modelo.rowCount()
        )

        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()

            cursor.execute(
                """
                SELECT
                    id_produtos,
                    nome,
                    descricao,
                    categoria,
                    preco,
                    estoque
                FROM produtos
                ORDER BY id_produtos
                """
            )

            produtos = cursor.fetchall()

            for produto in produtos:
                preco = Decimal(str(produto[4] or 0))

                linha = [
                    QStandardItem(str(produto[0] or "")),
                    QStandardItem(str(produto[1] or "")),
                    QStandardItem(str(produto[2] or "")),
                    QStandardItem(str(produto[3] or "")),
                    QStandardItem(
                        f"{preco:.2f}".replace(".", ",")
                    ),
                    QStandardItem(str(produto[5] or 0)),
                ]

                self.modelo.appendRow(linha)

            # Ajusta automaticamente a largura das colunas
            self.tela.tableView_2.resizeColumnsToContents()

        except Exception as erro:
            QMessageBox.critical(
                self.tela,
                "Erro",
                f"Erro ao carregar os produtos do banco:\n{erro}",
            )

        finally:
            if cursor is not None:
                cursor.close()

            if conexao is not None:
                conexao.close()

    def salvar_produto(self):
        """Cadastra um produto novo ou atualiza um produto existente."""

        codigo_texto = (
            self.tela.edit_codigo_produto.text().strip()
        )

        nome = (
            self.tela.edit_nome_produto.text().strip()
        )

        descricao = (
            self.tela.edit_descricao_produto.text().strip()
        )

        categoria = (
            self.tela.combo_categoria_produto
            .currentText()
            .strip()
        )

        preco_texto = (
            self.tela.edit_preco_produto.text().strip()
        )

        estoque_texto = (
            self.tela.edit_estoque_produto.text().strip()
        )

        # Validação do nome
        if not nome:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "Preencha o nome do produto.",
            )

            self.tela.edit_nome_produto.setFocus()
            return

        # Validação da descrição
        if not descricao:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "Preencha a descrição do produto.",
            )

            self.tela.edit_descricao_produto.setFocus()
            return

        # Validação da categoria
        if not categoria:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "Selecione uma categoria.",
            )

            self.tela.combo_categoria_produto.setFocus()
            return

        # Validação e conversão do preço
        try:
            preco_formatado = (
                preco_texto
                .replace("R$", "")
                .replace(" ", "")
                .replace(",", ".")
            )

            preco = Decimal(preco_formatado)

            if preco < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "Informe um preço válido. Exemplo: 49,90",
            )

            self.tela.edit_preco_produto.setFocus()
            return

        # Validação e conversão do estoque
        try:
            estoque = int(estoque_texto)

            if estoque < 0:
                raise ValueError

        except ValueError:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                (
                    "Informe um estoque válido usando um número "
                    "inteiro igual ou maior que zero."
                ),
            )

            self.tela.edit_estoque_produto.setFocus()
            return

        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()

            # Se o campo código estiver preenchido,
            # realiza a atualização do produto
            if codigo_texto:
                cursor.execute(
                    """
                    UPDATE produtos
                    SET
                        nome = %s,
                        descricao = %s,
                        categoria = %s,
                        preco = %s,
                        estoque = %s
                    WHERE id_produtos = %s
                    """,
                    (
                        nome,
                        descricao,
                        categoria,
                        preco,
                        estoque,
                        int(codigo_texto),
                    ),
                )

                mensagem = "Produto atualizado com sucesso!"

            # Se o campo código estiver vazio,
            # realiza um novo cadastro
            else:
                cursor.execute(
                    """
                    INSERT INTO produtos
                        (
                            nome,
                            descricao,
                            categoria,
                            preco,
                            estoque
                        )
                    VALUES
                        (%s, %s, %s, %s, %s)
                    """,
                    (
                        nome,
                        descricao,
                        categoria,
                        preco,
                        estoque,
                    ),
                )

                mensagem = "Produto cadastrado com sucesso!"

            conexao.commit()

            QMessageBox.information(
                self.tela,
                "Sucesso",
                mensagem,
            )

            self.limpar_campos()
            self.carregar_dados_na_tabela()

        except ValueError:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "O código do produto é inválido.",
            )

        except Exception as erro:
            if conexao is not None:
                conexao.rollback()

            QMessageBox.critical(
                self.tela,
                "Erro",
                f"Não foi possível salvar o produto:\n{erro}",
            )

        finally:
            if cursor is not None:
                cursor.close()

            if conexao is not None:
                conexao.close()

    def carregar_campos_ao_duplo_clique(self, index):
        """
        Carrega os dados do produto nos campos quando o usuário
        dá duplo clique em uma linha da tabela.
        """

        linha = index.row()

        def texto_coluna(coluna):
            item = self.modelo.item(linha, coluna)

            if item:
                return item.text()

            return ""

        # Código
        self.tela.edit_codigo_produto.setText(
            texto_coluna(0)
        )

        # Nome
        self.tela.edit_nome_produto.setText(
            texto_coluna(1)
        )

        # Descrição
        self.tela.edit_descricao_produto.setText(
            texto_coluna(2)
        )

        # Categoria
        categoria = texto_coluna(3)

        indice_categoria = (
            self.tela.combo_categoria_produto
            .findText(categoria)
        )

        if indice_categoria >= 0:
            self.tela.combo_categoria_produto.setCurrentIndex(
                indice_categoria
            )
        else:
            self.tela.combo_categoria_produto.addItem(
                categoria
            )

            self.tela.combo_categoria_produto.setCurrentText(
                categoria
            )

        # Preço
        self.tela.edit_preco_produto.setText(
            texto_coluna(4)
        )

        # Estoque
        self.tela.edit_estoque_produto.setText(
            texto_coluna(5)
        )

    def excluir_produto(self):
        """Exclui o produto selecionado do banco de dados."""

        codigo_texto = (
            self.tela.edit_codigo_produto.text().strip()
        )

        # Caso o código não esteja carregado nos campos,
        # tenta obter o código pela linha selecionada
        if not codigo_texto:
            linhas_selecionadas = (
                self.tela.tableView_2
                .selectionModel()
                .selectedRows()
            )

            if not linhas_selecionadas:
                QMessageBox.warning(
                    self.tela,
                    "Aviso",
                    "Selecione um produto na tabela.",
                )
                return

            linha = linhas_selecionadas[0].row()
            item_id = self.modelo.item(linha, 0)

            if item_id:
                codigo_texto = item_id.text()

        # Valida o código
        try:
            id_produto = int(codigo_texto)

        except ValueError:
            QMessageBox.warning(
                self.tela,
                "Aviso",
                "O código do produto é inválido.",
            )
            return

        # Confirmação da exclusão
        resposta = QMessageBox.question(
            self.tela,
            "Confirmar exclusão",
            (
                "Deseja realmente excluir o produto "
                f"de código {id_produto}?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if resposta != QMessageBox.StandardButton.Yes:
            return

        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()

            cursor.execute(
                """
                DELETE FROM produtos
                WHERE id_produtos = %s
                """,
                (id_produto,),
            )

            conexao.commit()

            if cursor.rowcount == 0:
                QMessageBox.warning(
                    self.tela,
                    "Aviso",
                    "Produto não encontrado no banco.",
                )
            else:
                QMessageBox.information(
                    self.tela,
                    "Sucesso",
                    "Produto excluído com sucesso!",
                )

            self.limpar_campos()
            self.carregar_dados_na_tabela()

        except Exception as erro:
            if conexao is not None:
                conexao.rollback()

            QMessageBox.critical(
                self.tela,
                "Erro",
                f"Não foi possível excluir o produto:\n{erro}",
            )

        finally:
            if cursor is not None:
                cursor.close()

            if conexao is not None:
                conexao.close()

    def limpar_campos(self):
        """Limpa os campos do formulário de produtos."""

        self.tela.edit_codigo_produto.clear()
        self.tela.edit_nome_produto.clear()
        self.tela.edit_descricao_produto.clear()
        self.tela.edit_preco_produto.clear()
        self.tela.edit_estoque_produto.clear()

        if self.tela.combo_categoria_produto.count() > 0:
            self.tela.combo_categoria_produto.setCurrentIndex(0)

        self.tela.tableView_2.clearSelection()
        self.tela.edit_nome_produto.setFocus()