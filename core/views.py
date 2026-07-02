from django.http import HttpResponse

def home_view(request):
    """
    Esta view retorna uma resposta HTTP simples com uma mensagem de teste.
    """
    html_content = "<h1>Apenas para teste do setup inicial</h1>"
    return HttpResponse(html_content)
