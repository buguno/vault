from decimal import Decimal

from django.utils.translation import gettext as _

from apps.core.pdf import Column, Heading, table_pdf
from apps.kits.services import KitStatus


def _plain(quantity: Decimal) -> str:
    return format(quantity.normalize(), 'f')


def kit_checklist_pdf(status: KitStatus) -> bytes:
    """A kit's checklist as a PDF, with a box to tick for each line."""
    kit = status.kit
    columns = [
        Column(_('Item'), 4),
        Column(_('In the kit'), 2, align_right=True),
        Column(_('Required'), 2, align_right=True),
    ]
    rows = []

    for line in status.lines:
        unit = str(line.item.unit_symbol)
        rows.append([
            line.item.name,
            f'{_plain(line.valid)} {unit}',
            f'{_plain(line.required)} {unit}',
        ])

    subtitle = kit.location.name

    if kit.description:
        subtitle = f'{subtitle} · {kit.description}'

    return table_pdf(
        Heading(kit.name, subtitle), columns, rows, checkboxes=True
    )
