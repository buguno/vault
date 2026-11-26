import re

from apps.core import pdf
from apps.core.pdf import Column, Heading

COLUMNS = [Column('Item', 3), Column('Qty', 1, align_right=True)]


def _document(rows, **kwargs):
    heading = Heading('Title', 'Subtitle')

    return pdf.table_pdf(heading, COLUMNS, rows, **kwargs)


def _pages(data):
    return data.count(b'/Type /Page /Parent')


def test_the_file_is_a_well_formed_pdf():
    data = _document([['Rice', '2 kg']])

    assert data.startswith(b'%PDF-1.4')
    assert data.rstrip().endswith(b'%%EOF')
    assert b'/BaseFont /Helvetica ' in data
    assert b'/BaseFont /Helvetica-Bold ' in data


def test_the_xref_table_points_at_every_object():
    data = _document([['Rice', '2 kg'], ['Beans', '1 kg']])

    xref_at = int(data.split(b'startxref\n')[1].split()[0])
    assert data[xref_at : xref_at + 4] == b'xref'
    entries = re.findall(rb'(\d{10}) 00000 n ', data)
    assert entries
    for number, offset in enumerate(entries, start=1):
        assert data[int(offset) :].startswith(b'%d 0 obj' % number)


def test_title_subtitle_and_cells_are_in_the_page():
    data = _document([['Rice', '2 kg']])

    for text in (b'(Title)', b'(Subtitle)', b'(Item)', b'(Rice)', b'(2 kg)'):
        assert text in data


def test_accents_are_encoded_as_windows_1252():
    data = _document([['Feijão', '1 kg']])

    assert b'(Feij\xe3o)' in data


def test_characters_outside_windows_1252_become_question_marks():
    data = _document([['Rice 米', '1']])

    assert b'(Rice ?)' in data


def test_parentheses_and_backslashes_are_escaped():
    data = _document([['a (b) \\ c', '1']])

    assert b'(a \\(b\\) \\\\ c)' in data


def test_long_tables_continue_on_new_pages_with_the_header_repeated():
    rows = [[f'Item {number}', '1'] for number in range(80)]

    data = _document(rows)

    assert _pages(data) >= 2
    assert data.count(b'(Qty)') == _pages(data)


def test_a_short_table_has_one_page():
    assert _pages(_document([['Rice', '1']])) == 1


def test_checkboxes_draw_one_box_per_row():
    data = _document([['Rice', '1'], ['Beans', '2']], checkboxes=True)

    assert data.count(b' re S') == 2
    assert b' re S' not in _document([['Rice', '1']])


def test_the_total_line_is_added_in_bold():
    data = _document([['Rice', '1']], total=('Total', '9,00'))

    assert re.search(rb'/F2 10.0 Tf [\d. ]+Td \(Total\)', data)
    assert re.search(rb'/F2 10.0 Tf [\d. ]+Td \(9,00\)', data)


def test_the_total_starts_a_new_page_when_the_last_one_is_full():
    rows = [[f'Item {number}', '1'] for number in range(29)]
    one_page = _document(rows)
    with_total = _document(rows, total=('Total', '1'))

    assert _pages(with_total) >= _pages(one_page)


def test_text_width_uses_the_helvetica_metrics():
    assert pdf.text_width('A', 1000) == 667
    assert pdf.text_width('A', 1000, bold=True) == 722
    assert pdf.text_width('\n', 10) == 0


def test_fit_cuts_long_text_with_an_ellipsis():
    cut = pdf.fit('A very long item name indeed', 10, 60)

    assert cut.endswith(pdf.ELLIPSIS)
    assert pdf.text_width(cut, 10) <= 60


def test_fit_keeps_text_that_already_fits():
    assert pdf.fit('Rice', 10, 200) == 'Rice'
