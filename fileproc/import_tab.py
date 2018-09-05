import openpyxl as pxl


def split_plain_text(fname, options):
    """ used options attributes:
            firstline, lastline, comment_sign, ignore_blank, row_sep, col_sep
            colcount.
        returns equal column size 2d array of stripped text entries
    """
    with open(fname, 'r') as f:
        lines = f.readlines()
    f.close()

    # firstline-lastline
    firstline = options.firstline
    lastline = options.lastline if options.lastline > 0 else len(lines)-1
    lines = lines[firstline:lastline+1]
    # remove text after comments
    if options.comment_sign:
        for i, line in enumerate(lines):
            pos = line.find(options.comment_sign)
            if pos >= 0:
                lines[i] = line[:pos]
    # remove blank lines
    if options.ignore_blank:
        lines = [x.strip() for x in lines]
        lines = list(filter(lambda x: len(x) > 0, lines))

    # reassemble lines if row separator is not a new line
    if options.row_sep != "newline":
        lines = " ".join(lines)
        if options.row_sep != "no (use column count)":
            lines = lines.split(options.row_sep)
        else:
            lines = [lines]

    # assemble columns
    if options.col_sep == 'whitespaces':
        for i, line in enumerate(lines):
            lines[i] = line.split()
    elif options.col_sep == 'tabular':
        for i, line in enumerate(lines):
            lines[i] = line.split('\t')
    elif options.col_sep == 'in double quotes':
        for i, line in enumerate(lines):
            lines[i] = line.split('"')[1::2]
    else:
        for i, line in enumerate(lines):
            lines[i] = line.split(options.col_sep)

    if len(lines) == 0:
        raise Exception("No data were loaded")

    # row split by column count
    if options.row_sep == "no (use column count)":
        lines2 = [lines[0][x:x+options.colcount]
                  for x in range(0, len(lines[0]), options.colcount)]
        lines = lines2

    # equal column count
    if options.colcount <= 0:
        cc = max([len(x) for x in lines])
    else:
        cc = options.colcount
    for i, line in enumerate(lines):
        if len(line) > cc:
            lines[i] = line[:cc]
        elif len(line) < cc:
            lines[i] = line + [""] * (cc - len(line))

    # final strip
    for line in lines:
        for j, x in enumerate(line):
            line[j] = x.strip()
    return lines


def read_xlsx_sheets(fname):
    return pxl.load_workbook(fname, read_only=True, data_only=True).sheetnames


def parse_xlsx_file(fname, options):
    doc = pxl.load_workbook(fname, read_only=True, data_only=True)
    sh = doc[options.sheetname]
    if options.range != '':
        min_col, min_row, max_col, max_row = pxl.utils.range_boundaries(
                options.range.upper())
    else:
        min_col, min_row = sh.min_column, sh.min_row
        max_col, max_row = sh.max_column, sh.max_row
    ret = []

    for row in sh.iter_rows(None, min_row, max_row, min_col, max_col):
        ret.append(list(map(lambda x: str(x.value)
                            if x.value is not None else None, row)))

    return ret
