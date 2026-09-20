import pdfplumber, re, csv, glob, os, sys

SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else '.'
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else '/tmp/pi_analise/out'
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# Fallback por OCR: algumas edicoes (ex.: 2024_01, 2024_04, 2024_05) tem
# a fonte embutida com o mapa de caracteres quebrado - o texto extraido
# normalmente vem cheio de "(cid:NN)" (pdfplumber) em vez das letras/numeros
# reais. Nesses casos, renderizamos a pagina como imagem e usamos OCR
# (tesseract) para ler o texto visualmente, que esta correto no PDF.
# O resultado fica em cache em disco (OCR e lento) para nao repetir entre execucoes.
OCR_CACHE_DIR = os.environ.get('FENABRAVE_OCR_CACHE', '/tmp/pi_analise/ocr_cache')
os.makedirs(OCR_CACHE_DIR, exist_ok=True)

def get_page_text(page, pdf_path, page_number):
    text = page.extract_text() or ''
    # aciona OCR tanto para fonte corrompida ("(cid:NN)") quanto para paginas
    # sem nenhuma camada de texto (ex.: 2023_09_2.pdf, aparentemente rasterizado -
    # extract_text() volta vazio mesmo a pagina tendo conteudo visivel)
    if '(cid:' not in text and len(text.strip()) >= 20:
        return text
    base = os.path.basename(pdf_path).replace('.pdf', '')
    cache_path = os.path.join(OCR_CACHE_DIR, f'{base}_p{page_number}.txt')
    if os.path.exists(cache_path):
        with open(cache_path, encoding='utf-8') as fh:
            return fh.read()
    try:
        from pdf2image import convert_from_path
        import pytesseract
        imgs = convert_from_path(pdf_path, first_page=page_number, last_page=page_number, dpi=200)
        ocr_text = pytesseract.image_to_string(imgs[0], lang='por')
    except Exception as e:
        print(f'  [OCR] falhou pag {page_number} de {pdf_path}: {e}', file=sys.stderr)
        ocr_text = text
    with open(cache_path, 'w', encoding='utf-8') as fh:
        fh.write(ocr_text)
    return ocr_text

MESES_PT = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',
            8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}

# =====================================================================
# NOTA IMPORTANTE (achado ao processar 2023-2026):
# A estrutura do relatorio NAO tem numero de pagina fixo entre edicoes:
#   - Edicoes de 2023 tem 46 paginas (SEM nenhuma secao "Mercado de
#     Eletrificados" - a Fenabrave só passou a publicar hibridos/eletricos
#     por fabricante a partir da edicao de Jan/2024, 52 paginas).
#   - A partir de Fev/2026 duas paginas (Resumo Mensal e Participacao por
#     motorizacao) perderam os rotulos de segmento ("A) Autos" etc.).
# Por isso a extracao NÃO usa mais indice fixo de pagina: ela varre todas
# as paginas do PDF e classifica cada uma pelo TITULO (4a linha de texto),
# de forma robusta a paginas que aparecem, somem ou mudam de posicao.
# =====================================================================

def undouble_line(line):
    """Em alguns PDFs (ex.: edicao de Jan/2022), texto em negrito 'falso' sai
    duplicado caractere a caractere (ex.: 'Total' -> 'TToottaall', 'Dez Jan
    Acumulado' -> 'DDeezz JJaann AAccuummuullaaddoo'). Isso faz cabecalhos nao
    serem reconhecidos como tal e acabam 'vazando' para o campo categoria.
    Colapsa, token a token, qualquer palavra em que cada caractere apareca
    duplicado em sequencia - teste estrito o suficiente para nao afetar
    texto normal (nenhuma palavra/numero real do relatorio passa nesse teste)."""
    tokens = line.split(' ')
    changed = False
    out = []
    for tok in tokens:
        if len(tok) >= 2 and len(tok) % 2 == 0:
            a, b = tok[0::2], tok[1::2]
            if a == b:
                out.append(a)
                changed = True
                continue
        out.append(tok)
    return ' '.join(out) if changed else line

def num(s):
    if s is None:
        return None
    s = s.strip()
    if s in ('0,00', '0'):
        return 0
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s) if '.' in s else int(s)
    except ValueError:
        return None

# classe de caracteres p/ nome de marca/modelo tolera minusculas (comum em OCR,
# que as vezes le o texto em caixa-alta do PDF original como minusculo)
RANK_MARCA_RE = re.compile(r'(\d+)º\s+([A-Za-zÀ-ÿ0-9\.\-\/\s]+?)\s+([\d\.]+)\s+([\d,]+)%')
RANK_MODELO_SIMPLES_RE = re.compile(r'(\d+)º\s+([A-Za-zÀ-ÿ0-9\.\-\/\s]+?)\s+([\d\.]+)(?=\s+\d+º|\s*$)')
MODELO_HIST_RE = re.compile(
    # o token de rank ("1º ...") as vezes sai corrompido no OCR ("jo", "pe", "e"...) -
    # o token em si e ignorado (o rank real e recalculado pela ordem no bloco, ver
    # parse_modelo_categoria_block); so o resto da linha precisa bater.
    # entre Jan e Acumulado ha um marcador de tendencia ("=" no texto normal;
    # no OCR sai como lixo tipo "wy"/"vw"/"A" - aceita qualquer token curto nao-numerico ali)
    r'^\S+\s+(.+?/.+?)\s+([\d\.,]+)\s+([\d\.,]+)\s*(?:[A-Za-zÀ-ÿ=]{1,3}\s+)?([\d\.,]+)\s+([\d,]+)%\s*$'
)
HEADER_LIKE_RE = re.compile(r'^[A-ZÀ-Ý0-9\s\+\.\-\']+$')

TITULOS_RECONHECIDOS = [
    'Emplacamento Automóveis e Comerciais Leves', 'Emplacamento Caminhões e Ônibus',
    'Emplacamento Motocicletas', 'Emplacamento Impl',
    'Resumo Mensal', 'Ranking dos emplacamentos em', 'Ranking dos emplacamentos acumulados',
    'Ranking por marca de emplac', 'Ranking por marca acumulado', 'Ranking por marca',
    'Participação por motorização', 'Mercado de Eletrificados',
    'Modelos mais emplac. venda direta acumulado', 'Modelos mais emplac. venda varejo acumulado',
    'Modelos mais emplacados venda direta', 'Modelos mais emplacados venda varejo',
    'Modelos mais emplacados acumulado até',
]

def find_titulo(text):
    """Procura, nas primeiras linhas da pagina, alguma que comece com um titulo
    conhecido. Usado em vez de indice fixo de linha porque paginas lidas via OCR
    (fallback de fonte corrompida) tem ruido extra antes/ao redor do titulo real."""
    for line in text.split('\n')[:10]:
        l = line.strip()
        for pat in TITULOS_RECONHECIDOS:
            if l.startswith(pat):
                return l
    return ''

def body_after_title(text):
    """Linhas apos o titulo da pagina (em vez de indice fixo lines[4:], que so
    vale para texto extraido normalmente - paginas OCR tem cabecalho diferente)."""
    lines = [undouble_line(l) for l in text.split('\n')]
    for i, line in enumerate(lines[:10]):
        l = line.strip()
        for pat in TITULOS_RECONHECIDOS:
            if l.startswith(pat):
                return lines[i + 1:]
    return lines[4:] if len(lines) > 4 else lines

def first_block_lines(lines):
    """Corta a lista de linhas assim que aparece um segundo bloco redundante
    (agregado 'X + Y' ou o mesmo ranking repetido como 'Acumulado')."""
    out = []
    seen_row = False
    for line in lines:
        l = line.strip()
        if re.match(r'^\d+º\s', l):
            seen_row = True
            out.append(line)
            continue
        if seen_row and l and (l == 'Acumulado' or HEADER_LIKE_RE.match(l)):
            break
        out.append(line)
    return out

def detect_columns_marca_or_modelo_simples(lines):
    """Descobre os segmentos das colunas a partir do cabecalho em maiusculas
    logo apos o titulo (ex.: 'AUTOMÓVEIS COMERCIAIS LEVES', 'CAMINHÕES ÔNIBUS', 'MOTOS')."""
    seg_map = {
        'AUTOMÓVEIS': 'Autos', 'COMERCIAIS LEVES': 'Com. Leves',
        'CAMINHÕES': 'Caminhões', 'ÔNIBUS': 'Ônibus', 'MOTOS': 'Motos',
    }
    checked = 0
    for line in lines:
        l = line.strip()
        if not l:
            continue  # ignora linhas em branco (comuns no OCR antes do cabecalho)
        if re.match(r'^\d+º', l):
            break  # ja chegou numa linha de dado, nao ha cabecalho de segmento
        checked += 1
        found = []
        tmp = l
        for k in ['AUTOMÓVEIS E COMERCIAIS LEVES']:
            if k in tmp:
                return None  # bloco agregado, nao usar
        for k in ['AUTOMÓVEIS', 'COMERCIAIS LEVES', 'CAMINHÕES', 'ÔNIBUS', 'MOTOS']:
            if k in tmp:
                found.append(seg_map[k])
                tmp = tmp.replace(k, '')
        if found:
            return found
        if checked >= 5:  # so vale a pena olhar poucas linhas de ruido antes do cabecalho
            break
    return None

def parse_ranking_marca_page(text):
    body = body_after_title(text)
    segmentos_ordem = detect_columns_marca_or_modelo_simples(body)
    if not segmentos_ordem:
        return []
    rows = []
    for line in first_block_lines(body):
        matches = RANK_MARCA_RE.findall(line)
        if not matches:
            continue
        for idx, (rank, fab, qty, part) in enumerate(matches):
            if idx >= len(segmentos_ordem):
                break
            rows.append({
                'segmento': segmentos_ordem[idx], 'rank': int(rank),
                'fabricante': fab.strip().upper(), 'quantidade_mes': num(qty),
                'participacao_pct': num(part),
            })
    return rows

def parse_ranking_modelo_simples_page(text):
    body = body_after_title(text)
    segmentos_ordem = detect_columns_marca_or_modelo_simples(body)
    if not segmentos_ordem:
        return []
    rows = []
    for line in first_block_lines(body):
        matches = RANK_MODELO_SIMPLES_RE.findall(line)
        if not matches:
            continue
        for idx, (rank, modelo, qty) in enumerate(matches):
            if idx >= len(segmentos_ordem):
                break
            rows.append({
                'segmento': segmentos_ordem[idx], 'rank': int(rank),
                'modelo': modelo.strip().upper(), 'quantidade_mes': num(qty),
            })
    return rows

def parse_modelo_categoria_block(lines, segmento, categoria):
    rows = []
    rank = 0  # recalculado pela ordem de aparicao no bloco (o digito original,
              # quando corrompido pelo OCR, e descartado - ver MODELO_HIST_RE)
    for line in lines:
        m = MODELO_HIST_RE.match(line.strip())
        if not m:
            continue
        rank += 1
        modelo, dez, jan, acum, part = m.groups()
        rows.append({
            'segmento': segmento, 'categoria': categoria, 'rank': rank,
            'modelo': modelo.strip().upper(), 'quantidade_mes': num(jan),
            'participacao_categoria_pct': num(part),
        })
    return rows

def parse_modelo_categoria_page(text, segmento_atual):
    """Retorna (rows, novo_segmento_atual). segmento_atual eh o contexto vindo
    da pagina anterior (mantido quando a pagina nao repete o marcador)."""
    body = body_after_title(text)
    rows = []
    current_cat = None
    buffer = []
    segmento = segmento_atual
    for line in body:
        l = line.strip()
        if l == 'COMERCIAIS LEVES':
            segmento = 'Com. Leves'; continue
        if l == 'CAMINHÕES':
            segmento = 'Caminhões'; continue
        if l == 'MOTOS':
            segmento = 'Motos'; continue
        if l.startswith('www.fenabrave'):
            continue
        if l.startswith('Sub Segmento') or re.match(r'^(AU|CO|CA|MO) - ', l) or l.startswith('Total 100%'):
            continue
        if re.match(r'^\d{4} \d{4} \d{4}', l) or l in ('2025 2026 2026',) or l.startswith('Modelo Part.') or l in ('Dez Jan Acumulado',):
            continue
        # cabecalho de coluna (normal ou ruido de OCR) - nunca eh nome de categoria.
        # O par de meses comparados muda conforme a edicao (Ago/Set, Jun/Jul, etc.),
        # entao 'Dez'/'Jan' literais so cobrem a edicao de Jan - o teste geral e
        # robusto pra qualquer mes: uma linha com 2+ anos (20xx) e sempre cabecalho,
        # nunca nome de categoria real.
        if ('Dez' in l and 'Jan' in l) or 'Acumulado' in l or len(re.findall(r'20\d{2}', l)) >= 2:
            continue
        # linha de dado: rank normal ("1º ...") OU rank corrompido por OCR (ex.: "1º"
        # lido como "jo"/"pe"/"e") - nesse caso o que sobra de confiavel e a presenca
        # de "/" (todo modelo eh MARCA/MODELO) terminando em "...NN,NN%"
        if re.match(r'^\d+º\s', l) or ('/' in l and re.search(r'\d[.,]?\d*%\s*$', l)):
            buffer.append(l); continue
        if l.startswith('Total '):
            if current_cat and buffer:
                rows.extend(parse_modelo_categoria_block(buffer, segmento, current_cat))
            buffer = []; current_cat = None; continue
        # so aceita um novo nome de categoria antes de comecar a acumular linhas de
        # dado (buffer vazio) - evita que ruido de OCR no meio de uma categoria
        # sobrescreva o nome ja identificado
        if l and not buffer and not re.match(r'^[\d,%\.\s=]+$', l):
            current_cat = l
    if current_cat and buffer:
        rows.extend(parse_modelo_categoria_block(buffer, segmento, current_cat))
    return rows, segmento

def parse_motorizacao(text):
    """Usa a POSICAO dos trios (nao o rotulo, que some a partir de Fev/2026)."""
    rows = []
    lines = text.split('\n')
    sub_labels = ['Até 1.0', 'De 1.0 Até 2.0', 'Acima de 2.0']
    segmentos_por_bloco = ['Autos', 'Com. Leves', None]
    valores = []
    for line in lines:
        l = line.strip()
        if l.startswith('Participação no acumulado'):
            break
        for sub in sub_labels:
            idx = l.find(sub)
            if idx != -1:
                nums = re.findall(r'-?\d[\d\.]*,\d+|-?\d[\d\.]*', l[idx + len(sub):])
                if nums:
                    valores.append((sub, num(nums[0])))
                break
    for i, (faixa, qtd) in enumerate(valores):
        bloco = i // 3
        if bloco >= len(segmentos_por_bloco):
            break
        segmento = segmentos_por_bloco[bloco]
        if segmento is None:
            continue
        rows.append({'segmento': segmento, 'faixa_motorizacao': faixa, 'quantidade_mes': qtd})
    return rows

# so casa nomes de segmento conhecidos (nao ".+") para nao capturar ruido de
# OCR que as vezes sobra no fim da linha do titulo (ex.: "Autos | OBB3)")
ELETRIFICADOS_SEGMENTO_RE = re.compile(
    r'Mercado de Eletrificados\s+(Autos e Comerciais Leves|Autos|Comerciais Leves|Caminhões|Ônibus|Motos)'
)

def parse_eletrificados_resumo(body_pre_ranking, segmento):
    """Extrai o bloco-resumo do topo da pagina de Eletrificados (ex.: 'A) Híbridos
    18.995 ...', 'B) Elétricos 8.198 ...', 'Tot.Eletrificados 27.193 ...') - sao os
    TOTAIS OFICIAIS do mes (nao limitados ao top-N de fabricantes do ranking abaixo)."""
    label_map = [
        (r'A\)?\s*H[ií]bridos', 'Híbridos'),
        (r'B\)?\s*El[ée]tricos', 'Elétricos'),
        (r'Tot\.?\s*Eletrificados', 'Total Eletrificados'),
    ]
    rows = []
    for pattern, nome in label_map:
        rx = re.compile(pattern)
        for line in body_pre_ranking:
            m = rx.search(line)
            if m:
                nums = re.findall(r'-?\d[\d\.]*,\d+|-?\d[\d\.]*', line[m.end():])
                if nums:
                    rows.append({'segmento': segmento, 'tipo_eletrificacao': nome,
                                 'quantidade_mes': num(nums[0].replace('.', ''))})
                break
    return rows

def parse_eletrificados_page(text):
    titulo = find_titulo(text)
    m = ELETRIFICADOS_SEGMENTO_RE.match(titulo)
    if not m:
        return [], []
    seg_raw = m.group(1).strip()
    if 'e Comerciais' in seg_raw or seg_raw == 'Autos e Comerciais Leves':
        return [], []  # bloco agregado, ignorar (derivavel)
    seg_map = {'Autos': 'Autos', 'Comerciais Leves': 'Com. Leves', 'Caminhões': 'Caminhões',
               'Ônibus': 'Ônibus', 'Motos': 'Motos'}
    segmento = seg_map.get(seg_raw, seg_raw)

    body = body_after_title(text)
    start_idx = None
    for i, l in enumerate(body):
        if 'MÊS' in l:
            start_idx = i; break
    resumo_rows = parse_eletrificados_resumo(body[:start_idx] if start_idx else body, segmento)
    if start_idx is None:
        return [], resumo_rows
    header = body[start_idx]
    tipos = re.findall(r'([A-ZÀ-Ý]+)\s+MÊS', header)
    rows = []
    for line in body[start_idx + 1:]:
        if 'ACUMULADO' in line:
            break
        matches = RANK_MARCA_RE.findall(line)
        if not matches:
            continue
        for idx, (rank, fab, qty, part) in enumerate(matches):
            if idx >= len(tipos):
                break
            rows.append({
                'segmento': segmento, 'tipo_eletrificacao': tipos[idx].capitalize(),
                'rank': int(rank), 'fabricante': fab.strip().upper(),
                'quantidade_mes': num(qty), 'participacao_pct': num(part),
            })
    return rows, resumo_rows

def parse_resumo_segmento(text):
    # padroes tolerantes a OCR (")" as vezes some, ex. "E) Motos" -> "E Motos")
    label_map = [
        (r'A\)?\s*Autos', "Autos"), (r'B\)?\s*Com\.?\s*Leves', "Com. Leves"),
        (r'A\s*\+\s*B', "Autos + Com. Leves"),
        (r'C\)?\s*Caminh[oõ]es', "Caminhões"), (r'D\)?\s*[OÔ]nibus', "Ônibus"),
        (r'C\s*\+\s*D', "Caminhões + Ônibus"),
        (r'Sub\s*[Tt]otal|Sire', "Subtotal (A a D)"), (r'E\)?\s*Motos', "Motos"),
        (r'F\)?\s*Impl\.?\s*Rod\.?', "Implementos Rodoviários"),
        (r'Outros', "Outros"), (r'Total', "Total Geral"),
    ]
    rows = []
    # a pagina tem uma 2a tabela ("Participação no acumulado", em %) com os
    # MESMOS rotulos de segmento - restringe a busca a antes dela, senao um
    # rotulo corrompido pelo OCR na 1a tabela pode "vazar" e pegar o valor
    # (percentual, nao quantidade) da 2a tabela por engano.
    corte = text.find('Participação no acumulado')
    texto_busca = text if corte == -1 else text[:corte]
    lines = texto_busca.split('\n')
    for pattern, nome in label_map:
        rx = re.compile(pattern)
        for line in lines:
            m = rx.search(line)
            if m:
                nums = re.findall(r'-?\d[\d\.]*,\d+|-?\d[\d\.]*', line[m.end():])
                if nums:
                    rows.append({'segmento': nome, 'quantidade_mes': num(nums[0].replace('.', ''))})
                break
    return rows

# =====================================================================
# Classificacao de paginas por titulo + varredura sequencial do PDF
# =====================================================================

def process_pdf(path, ctx):
    out = {'resumo': [], 'marca': [], 'modelo': [], 'modelo_cat': [], 'motorizacao': [], 'eletrificados': [], 'eletrificados_resumo': []}
    categoria_segmento_atual = 'Autos'  # reset a cada novo contexto "Emplacamento X"
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = get_page_text(page, path, page_number)
            titulo = find_titulo(text)

            if titulo.startswith('Emplacamento Automóveis e Comerciais Leves') or \
               titulo.startswith('Emplacamento Caminhões e Ônibus') or \
               titulo.startswith('Emplacamento Motocicletas') or \
               titulo.startswith('Emplacamento Impl'):
                categoria_segmento_atual = None  # proxima pagina de categoria deve trazer o marcador
                continue

            if titulo.startswith('Resumo Mensal'):
                for r in parse_resumo_segmento(text):
                    r.update(ctx); out['resumo'].append(r)
                continue

            if titulo.startswith('Ranking dos emplacamentos em'):
                for r in parse_ranking_modelo_simples_page(text):
                    r.update(ctx); r['tipo_venda'] = 'Total'; out['modelo'].append(r)
                continue

            if titulo.startswith('Ranking dos emplacamentos acumulados'):
                continue

            if titulo.startswith('Ranking por marca de emplac'):
                continue  # graficos de pizza (varejo/direta), redundante

            if titulo.startswith('Ranking por marca acumulado'):
                continue

            if titulo.startswith('Ranking por marca'):
                for r in parse_ranking_marca_page(text):
                    r.update(ctx); r['tipo_venda'] = 'Total'; out['marca'].append(r)
                continue

            if titulo.startswith('Participação por motorização'):
                for r in parse_motorizacao(text):
                    r.update(ctx); out['motorizacao'].append(r)
                continue

            if titulo.startswith('Mercado de Eletrificados'):
                rows, resumo_rows = parse_eletrificados_page(text)
                for r in rows:
                    r.update(ctx); out['eletrificados'].append(r)
                for r in resumo_rows:
                    r.update(ctx); out['eletrificados_resumo'].append(r)
                continue

            if titulo.startswith('Modelos mais emplac. venda direta acumulado') or \
               titulo.startswith('Modelos mais emplac. venda varejo acumulado'):
                continue

            if titulo.startswith('Modelos mais emplacados venda direta'):
                for r in parse_ranking_modelo_simples_page(text):
                    r.update(ctx); r['tipo_venda'] = 'Direta'; out['modelo'].append(r)
                continue

            if titulo.startswith('Modelos mais emplacados venda varejo'):
                for r in parse_ranking_modelo_simples_page(text):
                    r.update(ctx); r['tipo_venda'] = 'Varejo'; out['modelo'].append(r)
                continue

            if titulo.startswith('Modelos mais emplacados acumulado até'):
                rows, categoria_segmento_atual = parse_modelo_categoria_page(text, categoria_segmento_atual or 'Autos')
                for r in rows:
                    r.update(ctx); out['modelo_cat'].append(r)
                continue

            # demais paginas (graficos de pizza, texto, regioes) -> fora do escopo por ora
    return out

# =====================================================================
files = sorted(os.path.join(SRC_DIR, f) for f in os.listdir(SRC_DIR) if f.endswith('.pdf'))

agg = {'resumo': [], 'marca': [], 'modelo': [], 'modelo_cat': [], 'motorizacao': [], 'eletrificados': [], 'eletrificados_resumo': []}

for f in files:
    base = os.path.basename(f).replace('.pdf', '')
    parts = base.split('_')
    ano, mes_ref = int(parts[0]), int(parts[1])
    ctx = {'ano': ano, 'mes_num': mes_ref, 'mes_nome': MESES_PT[mes_ref]}
    print('processando', base, '...', file=sys.stderr)
    result = process_pdf(f, ctx)
    for k in agg:
        agg[k].extend(result[k])

def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(path, len(rows), 'linhas')

write_csv(os.path.join(OUT_DIR, 'fato_resumo_segmento.csv'), agg['resumo'],
          ['ano','mes_num','mes_nome','segmento','quantidade_mes'])
write_csv(os.path.join(OUT_DIR, 'fato_marca.csv'), agg['marca'],
          ['ano','mes_num','mes_nome','segmento','tipo_venda','rank','fabricante','quantidade_mes','participacao_pct'])
write_csv(os.path.join(OUT_DIR, 'fato_modelo.csv'), agg['modelo'],
          ['ano','mes_num','mes_nome','segmento','tipo_venda','rank','modelo','quantidade_mes'])
write_csv(os.path.join(OUT_DIR, 'fato_modelo_categoria.csv'), agg['modelo_cat'],
          ['ano','mes_num','mes_nome','segmento','categoria','rank','modelo','quantidade_mes','participacao_categoria_pct'])
write_csv(os.path.join(OUT_DIR, 'fato_motorizacao.csv'), agg['motorizacao'],
          ['ano','mes_num','mes_nome','segmento','faixa_motorizacao','quantidade_mes'])
write_csv(os.path.join(OUT_DIR, 'fato_eletrificados.csv'), agg['eletrificados'],
          ['ano','mes_num','mes_nome','segmento','tipo_eletrificacao','rank','fabricante','quantidade_mes','participacao_pct'])
write_csv(os.path.join(OUT_DIR, 'fato_eletrificados_resumo.csv'), agg['eletrificados_resumo'],
          ['ano','mes_num','mes_nome','segmento','tipo_eletrificacao','quantidade_mes'])
