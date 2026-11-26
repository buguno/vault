from datetime import date
from decimal import Decimal

from django.utils.formats import date_format
from django.utils.translation import gettext as _

from apps.core.pdf import Column, Heading, table_pdf
from apps.core.templatetags.money import money
from apps.inventory.services import ShoppingLine


def _plain(quantity: Decimal) -> str:
    return format(quantity.normalize(), 'f')


def shopping_list_pdf(
    lines: list[ShoppingLine], estimate: Decimal, today: date
) -> bytes:
    """The shopping list as a PDF, with a box to tick for each item."""
    columns = [
        Column(_('Item'), 3),
        Column(_('Category'), 2),
        Column(_('Have'), 1.4, align_right=True),
        Column(_('Minimum'), 1.2, align_right=True),
        Column(_('Buy'), 1.4, align_right=True),
        Column(_('Estimate'), 1.6, align_right=True),
    ]
    rows = []

    for line in lines:
        unit = str(line.item.unit_symbol)
        rows.append([
            line.item.name,
            line.item.category.name,
            f'{_plain(line.total)} {unit}',
            _plain(line.item.min_stock),
            f'{_plain(line.missing)} {unit}',
            money(line.estimate) if line.estimate is not None else '—',
        ])

    heading = Heading(_('Shopping list'), date_format(today, _('l, F j, Y')))

    return table_pdf(
        heading,
        columns,
        rows,
        total=(_('Estimated total'), money(estimate)) if estimate else None,
        checkboxes=True,
    )
