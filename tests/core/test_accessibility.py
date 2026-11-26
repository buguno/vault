import re
from http import HTTPStatus

import pytest
from django.contrib.messages import ERROR, SUCCESS
from django.contrib.messages.storage.base import Message
from django.template import Context, Template
from django.template.loader import render_to_string
from django.urls import reverse

from apps.core.forms import BackupForm


def _page(client, name, *args):
    return client.get(reverse(name, args=args)).content.decode()


def test_every_page_has_a_skip_link_to_the_main_content(auth_client):
    page = _page(auth_client, 'inventory:dashboard')

    assert 'class="skip-link"' in page
    assert 'href="#main"' in page
    assert re.search(r'<main id="main" tabindex="-1"', page)


def test_login_has_a_main_target_for_the_skip_link(client, db):
    page = client.get(reverse('core:login')).content.decode()

    assert 'href="#main"' in page
    assert '<main id="main"' in page


def test_the_current_page_is_marked_in_the_menu(auth_client):
    page = _page(auth_client, 'inventory:item_list')

    assert re.search(r'href="/items/"[^>]*aria-current="page"', page)
    assert not re.search(r'href="/kits/"[^>]*aria-current="page"', page)


def test_the_dashboard_is_current_only_on_the_dashboard(auth_client):
    page = _page(auth_client, 'inventory:dashboard')

    assert re.search(r'href="/"[^>]*aria-current="page"', page)
    assert not re.search(r'href="/items/"[^>]*aria-current="page"', page)


@pytest.mark.parametrize(
    ('path', 'expected'),
    [('/items/', 'aria-current="page"'), ('/kits/', '')],
)
def test_nav_current_tag(rf, path, expected):
    template = Template("{% load nav %}[{% nav_current '/items/' %}]")

    rendered = template.render(Context({'request': rf.get(path)}))

    assert rendered == f'[{expected}]'


def test_tables_name_their_columns(auth_client, item, batch):
    page = _page(auth_client, 'inventory:item_list')

    assert '<th scope="col"' in page
    assert '<th class=' not in page


def test_ids_on_the_item_page_are_unique(auth_client, batch):
    page = _page(auth_client, 'inventory:item_detail', batch.item_id)

    ids = re.findall(r'\sid="([^"]+)"', page)

    assert len(ids) == len(set(ids))
    assert 'entry-quantity' in ids
    assert f'adjust-{batch.pk}-new_quantity' in ids


def test_an_invalid_field_is_linked_to_its_error(auth_client, item, location):
    response = auth_client.post(
        reverse('inventory:item_entry', args=[item.pk]),
        {'location': location.pk, 'quantity': '-1'},
    )

    page = response.content.decode()
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert 'aria-invalid="true"' in page
    assert 'aria-describedby="entry-quantity-error"' in page
    assert 'id="entry-quantity-error"' in page
    assert 'role="alert"' in page


def test_several_errors_get_a_summary_with_links(auth_client, item):
    response = auth_client.post(
        reverse('inventory:item_entry', args=[item.pk]), {}
    )

    page = response.content.decode()
    assert 'Corrija estes campos:' in page
    assert 'href="#entry-location"' in page
    assert 'href="#entry-quantity"' in page


def test_help_text_is_linked_to_its_field(auth_client, item):
    page = _page(auth_client, 'inventory:item_detail', item.pk)

    assert 'aria-describedby="entry-expires_at-help"' in page
    assert 'id="entry-expires_at-help"' in page


def test_required_fields_are_marked(auth_client, item):
    page = _page(auth_client, 'inventory:item_detail', item.pk)

    assert re.search(
        r'for="entry-quantity"[^>]*>Quantidade<span aria-hidden', page
    )


def test_a_valid_form_carries_no_error_attributes():
    form = BackupForm({'passphrase': 'x' * 12, 'passphrase_again': 'x' * 12})

    assert form.is_valid()
    attrs = form.fields['passphrase'].widget.attrs
    assert 'aria-invalid' not in attrs
    assert attrs['aria-describedby'] == 'id_passphrase-help'


def test_an_invalid_form_marks_only_the_wrong_field():
    form = BackupForm({'passphrase': 'x' * 12, 'passphrase_again': 'y' * 12})

    assert not form.is_valid()
    again = form.fields['passphrase_again'].widget.attrs
    assert again['aria-invalid'] == 'true'
    assert again['aria-describedby'] == 'id_passphrase_again-error'
    assert 'aria-invalid' not in form.fields['passphrase'].widget.attrs


def test_the_login_page_shows_which_field_is_wrong(client, db):
    response = client.post(
        reverse('core:login'), {'username': '', 'password': ''}
    )

    page = response.content.decode()
    assert 'aria-invalid="true"' in page
    assert 'id="id_username-error"' in page


@pytest.mark.parametrize(
    ('level', 'role'), [(ERROR, 'alert'), (SUCCESS, 'status')]
)
def test_errors_interrupt_and_the_rest_are_polite(level, role):
    html = render_to_string(
        'partials/messages.html', {'messages': [Message(level, 'Saved')]}
    )

    assert f'role="{role}"' in html


def test_decorative_bars_are_hidden_from_assistive_tech(auth_client, item):
    item.min_stock = 5
    item.save()

    page = _page(auth_client, 'inventory:dashboard')

    assert 'aria-hidden="true" class="track' in page


def test_menu_links_keep_their_layout_classes(auth_client):
    page = _page(auth_client, 'inventory:dashboard')

    links = re.findall(r'<a href="[^"]*" class="([^"]*)"[^>]*>\s*<svg', page)

    assert links
    assert all('\\' not in link for link in links)
    assert all(link.startswith('flex items-center') for link in links)
    assert '\\"' not in page
