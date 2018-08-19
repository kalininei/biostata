from bdata import bsqlproc
import openpyxl as pxl


def model_export(model, opt):
    if opt.format == 'plain text':
        return plain_text_export(model, opt)
    elif opt.format == 'xlsx':
        return xlsx_export(model, opt)
    else:
        raise NotImplementedError


def _get_data_lines(datatab, opt):
    lines = []
    if opt.with_caption:
        lines.append([datatab.column_caption(i)
                      for i in range(datatab.n_cols())])

    for i in range(datatab.n_rows()):
        rvals = [None]*datatab.n_cols()
        for j, col in enumerate(datatab.visible_columns):
            rvals[j] = datatab.tab.get_value(i, j)

            if rvals[j] is not None and not opt.numeric_enums:
                rvals[j] = col.repr(rvals[j])

            if rvals[j] is None and col.is_category and\
                    datatab.n_subrows(i) > 1:
                if opt.grouped_categories == 'Comma separated':
                    vals = datatab.get_subvalues(i, j)
                    if not opt.numeric_enums:
                        vals = map(col.repr, vals)
                    rvals[j] = ','.join(map(str, vals))
                elif opt.grouped_categories == 'Unique count':
                    n_uni = datatab.n_subdata_unique(i, j)
                    rvals[j] = bsqlproc.group_repr(n_uni)
                elif opt.grouped_categories == 'None':
                    rvals[j] = ''

        lines.append(rvals)

    if not opt.with_id:
        lines = [x[1:] for x in lines]

    return lines


def plain_text_export(datatab, opt):
    lines = _get_data_lines(datatab, opt)

    if not opt.with_id:
        lines = [x[1:] for x in lines]
    lines = ['\t'.join(map(str, x)) + '\n' for x in lines]

    with open(opt.filename, 'w') as fid:
        fid.writelines(lines)
    fid.close()


def xlsx_export(datatab, opt):
    lines = _get_data_lines(datatab, opt)

    wb = pxl.Workbook()
    ws1 = wb.active
    ws1.title = datatab.table_name()
    for line in lines:
        ws1.append(list(line))
    wb.save(opt.filename)
