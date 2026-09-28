"""Ferramenta Jupyter; não participa do treinamento nem é importada pelo notebook."""
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main():
    pasta = Path(__file__).resolve().parent
    arquivo = pasta / "and_perceptron_adaline.ipynb"
    notebook = nbformat.read(arquivo, as_version=4)
    nbformat.validate(notebook)
    NotebookClient(
        notebook, timeout=120, kernel_name="python3", skip_cells_with_tag="interativa",
        resources={"metadata": {"path": str(pasta)}},
    ).execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, arquivo)
    print("Notebook executado em kernel novo; resultados e figuras gravados.")
    print("Célula final interativa preservada para execução manual no Jupyter.")


if __name__ == "__main__":
    main()
