from datetime import datetime
from decimal import Decimal, InvalidOperation

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QMessageBox, QTableWidgetItem

from utils.cnn import conectar


class GerenciadorVendas:
    """Gerencia o registro, a listagem e a exclusão das vendas."""

    def __init__(self, tela):
        self.tela = tela
        self.produtos = {}

        # tableView_vendas é um QTableWidget no arquivo .ui.
        self.tabela = self.tela.tableView_vendas
        self.tabela.setColumnCount(7)
        self.tabela.setHorizontalHeaderLabels([
            "Código",
            "Data/Hora",
            "Cliente",
            "Produto",
            "Quantidade",
            "Valor unitário",
            "Valor total",
        ])
        self.tabela.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tabela.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tabela.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.tela.btn_salvar_6.clicked.connect(self.registrar_venda)
        self.tela.btn_limpar_6.clicked.connect(self.limpar_campos)
        self.tela.btn_excluir_6.clicked.connect(self.excluir_venda)
        self.tela.combo_produtos_vendas.currentIndexChanged.connect(
            self.atualizar_quantidades
        )
        self.tela.edit_quantidade.textChanged.connect(
            self.atualizar_valor_venda
        )

        self.carregar_clientes()
        self.carregar_produtos()
        self.carregar_vendas()

    @staticmethod
    def formatar_moeda(valor):
        return f"R$ {Decimal(str(valor or 0)):.2f}".replace(".", ",")

    def carregar_clientes(self):
        self.tela.combo_cliente_vendas.clear()
        self.tela.combo_cliente_vendas.addItem("Selecione o cliente", None)
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT id_clientes, nome FROM clientes ORDER BY nome"
            )
            for id_cliente, nome in cursor.fetchall():
                self.tela.combo_cliente_vendas.addItem(nome, id_cliente)
        except Exception as erro:
            QMessageBox.critical(
                self.tela, "Erro", f"Erro ao carregar clientes:\n{erro}"
            )
        finally:
            if cursor is not None:
                cursor.close()
            if conexao is not None:
                conexao.close()

    def carregar_produtos(self):
        self.produtos.clear()
        self.tela.combo_produtos_vendas.clear()
        self.tela.combo_produtos_vendas.addItem("Selecione o produto", None)
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT id_produtos, nome, preco, estoque
                FROM produtos
                WHERE estoque > 0
                ORDER BY nome
                """
            )
            for id_produto, nome, preco, estoque in cursor.fetchall():
                self.produtos[int(id_produto)] = {
                    "preco": Decimal(str(preco)),
                    "estoque": int(estoque),
                }
                texto = f"{nome} - {self.formatar_moeda(preco)}"
                self.tela.combo_produtos_vendas.addItem(texto, id_produto)
        except Exception as erro:
            QMessageBox.critical(
                self.tela, "Erro", f"Erro ao carregar produtos:\n{erro}"
            )
        finally:
            if cursor is not None:
                cursor.close()
            if conexao is not None:
                conexao.close()

        self.atualizar_quantidades()

    def atualizar_quantidades(self):
        """Atualiza o limite permitido conforme o estoque do produto."""
        id_produto = self.tela.combo_produtos_vendas.currentData()
        produto = self.produtos.get(id_produto)

        self.tela.edit_quantidade.clear()
        if produto:
            self.tela.edit_quantidade.setPlaceholderText(
                f"Disponível: {produto['estoque']}"
            )
        else:
            self.tela.edit_quantidade.setPlaceholderText("Quantidade")

        self.atualizar_valor_venda()

    def atualizar_valor_venda(self):
        id_produto = self.tela.combo_produtos_vendas.currentData()
        produto = self.produtos.get(id_produto)
        quantidade_texto = self.tela.edit_quantidade.text().strip()

        try:
            quantidade = int(quantidade_texto)
        except ValueError:
            quantidade = 0

        if produto and quantidade > 0:
            total = produto["preco"] * quantidade
            self.tela.valor_venda.setText(self.formatar_moeda(total))
        else:
            self.tela.valor_venda.setText("R$ 0,00")

    def registrar_venda(self):
        id_cliente = self.tela.combo_cliente_vendas.currentData()
        id_produto = self.tela.combo_produtos_vendas.currentData()
        quantidade_texto = self.tela.edit_quantidade.text().strip()
        produto = self.produtos.get(id_produto)

        try:
            quantidade = int(quantidade_texto)
        except ValueError:
            quantidade = 0

        if id_cliente is None:
            QMessageBox.warning(self.tela, "Aviso", "Selecione um cliente.")
            return
        if id_produto is None or produto is None:
            QMessageBox.warning(self.tela, "Aviso", "Selecione um produto.")
            return
        if quantidade is None or quantidade <= 0:
            QMessageBox.warning(self.tela, "Aviso", "Selecione a quantidade.")
            return
        if quantidade > produto["estoque"]:
            QMessageBox.warning(
                self.tela, "Aviso", "A quantidade é maior que o estoque disponível."
            )
            return

        valor_total = produto["preco"] * quantidade
        data_venda = datetime.now()
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()

            # Confere novamente o estoque dentro da operação.
            cursor.execute(
                "SELECT estoque FROM produtos WHERE id_produtos = %s FOR UPDATE",
                (id_produto,),
            )
            resultado = cursor.fetchone()
            if resultado is None or int(resultado[0]) < quantidade:
                conexao.rollback()
                QMessageBox.warning(
                    self.tela, "Aviso", "Estoque insuficiente para registrar a venda."
                )
                self.carregar_produtos()
                return

            cursor.execute(
                """
                INSERT INTO vendas
                    (id_clientes, id_produtos, quantidade, valor_total, data_venda)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_cliente, id_produto, quantidade, valor_total, data_venda),
            )
            cursor.execute(
                """
                UPDATE produtos
                SET estoque = estoque - %s
                WHERE id_produtos = %s
                """,
                (quantidade, id_produto),
            )
            conexao.commit()

            QMessageBox.information(
                self.tela, "Sucesso", "Venda registrada com sucesso!"
            )
            self.limpar_campos()
            self.carregar_produtos()
            self.carregar_vendas()

        except (InvalidOperation, ValueError) as erro:
            if conexao is not None:
                conexao.rollback()
            QMessageBox.critical(self.tela, "Erro", f"Valor inválido:\n{erro}")
        except Exception as erro:
            if conexao is not None:
                conexao.rollback()
            QMessageBox.critical(
                self.tela, "Erro", f"Não foi possível registrar a venda:\n{erro}"
            )
        finally:
            if cursor is not None:
                cursor.close()
            if conexao is not None:
                conexao.close()

    def carregar_vendas(self):
        self.tabela.setRowCount(0)
        conexao = None
        cursor = None

        try:
            conexao = conectar()
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT
                    v.id_vendas,
                    v.data_venda,
                    c.nome,
                    p.nome,
                    v.quantidade,
                    (v.valor_total / NULLIF(v.quantidade, 0)) AS valor_unitario,
                    v.valor_total
                FROM vendas AS v
                INNER JOIN clientes AS c
                    ON c.id_clientes = v.id_clientes
                INNER JOIN produtos AS p
                    ON p.id_produtos = v.id_produtos
                ORDER BY v.id_vendas DESC
                """
            )

            for venda in cursor.fetchall():
                linha = self.tabela.rowCount()
                self.tabela.insertRow(linha)

                data = venda[1]
                if hasattr(data, "strftime"):
                    data_formatada = data.strftime("%d/%m/%Y %H:%M")
                else:
                    data_formatada = str(data or "")

                valores = [
                    str(venda[0]),
                    data_formatada,
                    str(venda[2]),
                    str(venda[3]),
                    str(venda[4]),
                    self.formatar_moeda(venda[5]),
                    self.formatar_moeda(venda[6]),
                ]

                for coluna, valor in enumerate(valores):
                    item = QTableWidgetItem(valor)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter
                        | Qt.AlignmentFlag.AlignLeft
                    )
                    self.tabela.setItem(linha, coluna, item)

            self.tabela.resizeColumnsToContents()

        except Exception as erro:
            QMessageBox.critical(
                self.tela, "Erro", f"Erro ao carregar as vendas:\n{erro}"
            )
        finally:
            if cursor is not None:
                cursor.close()
            if conexao is not None:
                conexao.close()

    def excluir_venda(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.warning(
                self.tela, "Aviso", "Selecione uma venda na tabela."
            )
            return

        item_id = self.tabela.item(linha, 0)
        if item_id is None:
            QMessageBox.warning(
                self.tela, "Aviso", "Não foi possível identificar a venda."
            )
            return

        id_venda = int(item_id.text())
        resposta = QMessageBox.question(
            self.tela,
            "Confirmar exclusão",
            f"Deseja realmente excluir a venda de código {id_venda}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
                SELECT id_produtos, quantidade
                FROM vendas
                WHERE id_vendas = %s
                FOR UPDATE
                """,
                (id_venda,),
            )
            venda = cursor.fetchone()
            if venda is None:
                conexao.rollback()
                QMessageBox.warning(self.tela, "Aviso", "Venda não encontrada.")
                self.carregar_vendas()
                return

            id_produto, quantidade = venda
            cursor.execute(
                "DELETE FROM vendas WHERE id_vendas = %s", (id_venda,)
            )
            cursor.execute(
                """
                UPDATE produtos
                SET estoque = estoque + %s
                WHERE id_produtos = %s
                """,
                (quantidade, id_produto),
            )
            conexao.commit()

            QMessageBox.information(
                self.tela, "Sucesso", "Venda excluída e estoque devolvido!"
            )
            self.carregar_produtos()
            self.carregar_vendas()

        except Exception as erro:
            if conexao is not None:
                conexao.rollback()
            QMessageBox.critical(
                self.tela, "Erro", f"Não foi possível excluir a venda:\n{erro}"
            )
        finally:
            if cursor is not None:
                cursor.close()
            if conexao is not None:
                conexao.close()

    def limpar_campos(self):
        self.tela.combo_cliente_vendas.setCurrentIndex(0)
        self.tela.combo_produtos_vendas.setCurrentIndex(0)
        self.tela.edit_quantidade.clear()
        self.tela.edit_quantidade.setPlaceholderText("Quantidade")
        self.tabela.clearSelection()
        self.tela.valor_venda.setText("R$ 0,00")