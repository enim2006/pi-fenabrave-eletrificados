"""
Atualizacao incremental dos 7 CSVs fato: processa so o(s) PDF(s) informado(s)
(um novo mes, ou um mes que precise ser reprocessado por correcao) e faz
merge nos CSVs existentes em vez de reconstruir tudo do zero.

Seguro porque process_pdf() (importado de extract_fenabrave.py) e' totalmente
independente por arquivo - nenhum fato depende de dado de outro mes.

Idempotente: se o(s) mes(es) do PDF ja existirem no CSV, as linhas antigas
desse(s) mes(es) sao substituidas (nao duplicadas) - util tanto para adicionar
um mes novo quanto para reprocessar um mes ja existente apos correcao no
parser.

Uso:
    python3 update_fenabrave.py OUT_DIR arquivo1.pdf [arquivo2.pdf ...]

Exemplo (adicionar setembro/2026 aos CSVs em 02_dados_extraidos/):
    python3 update_fenabrave.py ../../02_dados_extraidos ../../01_dados_brutos/2026_09_02.pdf

Node: nao precisa que os PDFs estejam na mesma pasta dos ja processados -
so o nome do arquivo precisa seguir o padrao AAAA_MM_*.pdf.
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_fenabrave import process_pdf, MESES_PT, FIELDNAMES, FATO_FILENAME, write_csv


def read_csv_rows(path, fieldnames):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def sort_key(row):
    return (int(row['ano']), int(row['mes_num']))


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    out_dir = sys.argv[1]
    pdf_paths = sys.argv[2:]

    novos_meses = set()
    agg_novos = {k: [] for k in FATO_FILENAME}

    for pdf_path in pdf_paths:
        base = os.path.basename(pdf_path).replace('.pdf', '')
        parts = base.split('_')
        ano, mes_ref = int(parts[0]), int(parts[1])
        novos_meses.add((ano, mes_ref))
        ctx = {'ano': ano, 'mes_num': mes_ref, 'mes_nome': MESES_PT[mes_ref]}
        print('processando (incremental)', base, '...', file=sys.stderr)
        result = process_pdf(pdf_path, ctx)
        for k in agg_novos:
            agg_novos[k].extend(result[k])

    for k, fname in FATO_FILENAME.items():
        path = os.path.join(out_dir, fname)
        existentes = read_csv_rows(path, FIELDNAMES[k])
        # remove linhas antigas dos meses que estao sendo (re)processados —
        # torna a operacao idempotente (reprocessar um mes so substitui, nao duplica)
        mantidas = [r for r in existentes if (int(r['ano']), int(r['mes_num'])) not in novos_meses]
        combinadas = mantidas + agg_novos[k]
        combinadas.sort(key=sort_key)
        write_csv(path, combinadas, FIELDNAMES[k])


if __name__ == '__main__':
    main()
