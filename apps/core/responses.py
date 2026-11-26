from django.http import HttpResponse


def pdf_response(data: bytes, filename: str) -> HttpResponse:
    """A PDF the browser downloads under `filename`."""
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
