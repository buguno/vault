"""A tiny PDF writer for simple tables, with no third-party library.

It draws a title, a subtitle and a table on A4 pages using the standard PDF
fonts Helvetica and Helvetica-Bold, which every viewer has, so nothing is
embedded. Text is encoded as Windows-1252 (Portuguese and English are fine;
characters outside it become `?`). Long tables continue on new pages and repeat
the header.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from apps.core.pdf_metrics import FIRST_CODE, HELVETICA, HELVETICA_BOLD

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 42
TITLE_SIZE = 20
SUBTITLE_SIZE = 10
TEXT_SIZE = 10
HEADER_SIZE = 9
ROW_HEIGHT = 24
BASELINE_OFFSET = 9  # from the bottom of a row to its text
CELL_PADDING = 4
BOX_SIZE = 9
BOX_COLUMN = 22
ELLIPSIS = '…'
INK = '0 g'
MUTED = '0.45 g'
RULE = '0.8 G'


@dataclass(frozen=True)
class Column:
    title: str
    weight: float = 1.0  # share of the table width
    align_right: bool = False


@dataclass(frozen=True)
class Heading:
    title: str
    subtitle: str


@dataclass(frozen=True)
class Style:
    size: float = TEXT_SIZE
    bold: bool = False
    color: str = INK


def text_width(text: str, size: float, bold: bool = False) -> float:
    """Width of `text` in points when set in Helvetica at `size`."""
    widths = HELVETICA_BOLD if bold else HELVETICA
    data = text.encode('cp1252', errors='replace')
    units = sum(
        widths[code - FIRST_CODE] if code >= FIRST_CODE else 0 for code in data
    )

    return units * size / 1000


def fit(text: str, size: float, room: float, bold: bool = False) -> str:
    """`text` cut with an ellipsis so it is not wider than `room`."""
    if text_width(text, size, bold) <= room:
        return text

    while text and text_width(text + ELLIPSIS, size, bold) > room:
        text = text[:-1]

    return text + ELLIPSIS


def _escape(text: str) -> bytes:
    data = text.encode('cp1252', errors='replace')

    return (
        data
        .replace(b'\\', b'\\\\')
        .replace(b'(', b'\\(')
        .replace(b')', b'\\)')
    )


class _Page:
    """The drawing commands of one page, from the top down."""

    def __init__(self) -> None:
        self.commands: list[bytes] = []
        self.y = PAGE_HEIGHT - MARGIN

    def text(self, x: float, y: float, text: str, style: Style) -> None:
        """A line of text with its baseline at `y`."""
        font = b'F2' if style.bold else b'F1'
        self.commands.append(
            b'BT %s /%s %.1f Tf %.2f %.2f Td ('
            % (style.color.encode(), font, style.size, x, y)
            + _escape(text)
            + b') Tj ET'
        )

    def line(self, y: float, width: float = 0.5) -> None:
        """A rule across the table at height `y`."""
        self.commands.append(
            b'%s %.2f w %.2f %.2f m %.2f %.2f l S'
            % (RULE.encode(), width, MARGIN, y, PAGE_WIDTH - MARGIN, y)
        )

    def box(self, x: float, y: float) -> None:
        """An empty square to tick."""
        self.commands.append(
            b'0.4 G 0.7 w %.2f %.2f %d %d re S' % (x, y, BOX_SIZE, BOX_SIZE)
        )


class TablePdf:
    """Builds a one-table document; see `table_pdf` for the usual call."""

    def __init__(
        self, heading: Heading, columns: Sequence[Column], checkboxes: bool
    ) -> None:
        self.heading = heading
        self.columns = columns
        self.checkboxes = checkboxes
        self.pages: list[_Page] = []
        self.edges = self._column_edges()
        self._new_page(first=True)

    def _column_edges(self) -> list[tuple[float, float]]:
        left = MARGIN + (BOX_COLUMN if self.checkboxes else 0)
        room = PAGE_WIDTH - MARGIN - left
        weights = sum(column.weight for column in self.columns)
        edges = []

        for column in self.columns:
            width = room * column.weight / weights
            edges.append((left, left + width))
            left += width

        return edges

    @property
    def page(self) -> _Page:
        return self.pages[-1]

    def _new_page(self, first: bool = False) -> None:
        self.pages.append(_Page())

        if first:
            self._heading()

        self._header()

    def _heading(self) -> None:
        self.page.y -= TITLE_SIZE
        self.page.text(
            MARGIN,
            self.page.y,
            self.heading.title,
            Style(TITLE_SIZE, bold=True),
        )

        self.page.y -= SUBTITLE_SIZE + 6
        subtitle = fit(
            self.heading.subtitle, SUBTITLE_SIZE, PAGE_WIDTH - 2 * MARGIN
        )
        self.page.text(
            MARGIN, self.page.y, subtitle, Style(SUBTITLE_SIZE, color=MUTED)
        )

        self.page.y -= 22

    def _cell(self, index: int, y: float, text: str, style: Style) -> None:
        left, right = self.edges[index]
        room = right - left - 2 * CELL_PADDING
        text = fit(text, style.size, room, style.bold)

        if self.columns[index].align_right:
            width = text_width(text, style.size, style.bold)
            x = right - CELL_PADDING - width
        else:
            x = left + CELL_PADDING

        self.page.text(x, y, text, style)

    def _header(self) -> None:
        baseline = self.page.y - ROW_HEIGHT + BASELINE_OFFSET
        style = Style(HEADER_SIZE, bold=True, color=MUTED)

        for index, column in enumerate(self.columns):
            self._cell(index, baseline, column.title, style)

        self.page.y -= ROW_HEIGHT
        self.page.line(self.page.y, 0.8)

    def _make_room(self) -> None:
        if self.page.y - ROW_HEIGHT < MARGIN:
            self._new_page()

    def row(self, cells: Sequence[str]) -> None:
        self._make_room()
        baseline = self.page.y - ROW_HEIGHT + BASELINE_OFFSET

        for index, text in enumerate(cells):
            style = Style(bold=index == 0, color=INK if index == 0 else MUTED)
            self._cell(index, baseline, text, style)

        self.page.y -= ROW_HEIGHT
        self.page.line(self.page.y)

    def checkbox(self) -> None:
        """A box to tick, for the row that was just added."""
        y = self.page.y + (ROW_HEIGHT - BOX_SIZE) / 2
        self.page.box(MARGIN + 2, y)

    def total(self, label: str, value: str) -> None:
        """A bold last line: the label ends where the last column starts."""
        self._make_room()
        baseline = self.page.y - ROW_HEIGHT + BASELINE_OFFSET
        style = Style(bold=True)
        last_left, _ = self.edges[-1]
        label_width = text_width(label, style.size, style.bold)

        self.page.text(
            last_left - label_width - CELL_PADDING, baseline, label, style
        )
        self._cell(len(self.columns) - 1, baseline, value, style)
        self.page.y -= ROW_HEIGHT

    def render(self) -> bytes:
        objects: list[bytes] = [
            b'<< /Type /Catalog /Pages 2 0 R >>',
            b'',  # the page tree, filled in once the pages are known
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
            b'/Encoding /WinAnsiEncoding >>',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold '
            b'/Encoding /WinAnsiEncoding >>',
        ]
        kids = []

        for page in self.pages:
            stream = b'\n'.join(page.commands)
            objects.append(
                b'<< /Length %d >>\nstream\n%s\nendstream'
                % (len(stream), stream)
            )
            contents = len(objects)
            objects.append(
                b'<< /Type /Page /Parent 2 0 R '
                b'/MediaBox [0 0 %d %d] '
                b'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> '
                b'/Contents %d 0 R >>' % (PAGE_WIDTH, PAGE_HEIGHT, contents)
            )
            kids.append(b'%d 0 R' % len(objects))

        objects[1] = b'<< /Type /Pages /Kids [%s] /Count %d >>' % (
            b' '.join(kids),
            len(kids),
        )

        return _serialize(objects)


def _serialize(objects: list[bytes]) -> bytes:
    """The objects as a file: header, body, cross-reference table, trailer."""
    out = bytearray(b'%PDF-1.4\n')
    offsets = []

    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n%s\nendobj\n' % (number, body)

    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)

    for offset in offsets:
        out += b'%010d 00000 n \n' % offset

    out += b'trailer\n<< /Size %d /Root 1 0 R >>\n' % (len(objects) + 1)
    out += b'startxref\n%d\n%%%%EOF\n' % xref

    return bytes(out)


def table_pdf(
    heading: Heading,
    columns: Sequence[Column],
    rows: Sequence[Sequence[str]],
    total: tuple[str, str] | None = None,
    checkboxes: bool = False,
) -> bytes:
    """A PDF with a title, a subtitle and one table.

    `rows` hold one string per column. `total` is an optional last line as
    `(label, value)`, the value under the last column. With `checkboxes`,
    every row starts with a box to tick.
    """
    document = TablePdf(heading, columns, checkboxes)

    for cells in rows:
        document.row(cells)

        if checkboxes:
            document.checkbox()

    if total:
        document.total(*total)

    return document.render()
