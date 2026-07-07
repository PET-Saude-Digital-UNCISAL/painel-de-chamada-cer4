from django.http import HttpResponse

def home_view(request):
    """
    Esta view retorna uma resposta HTTP simples com uma mensagem de teste.
    """
    html_content = "<h1>Apenas para teste do setup inicial</h1>"
    return HttpResponse(html_content)
def perdeu_chamada_view(request):
    html_content = "<h1>Tela de Pacientes que Perderam a Chamada</h1><p>Em breve a listagem aqui!</p>"
    return HttpResponse(html_content)