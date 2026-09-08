from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PainelChamadaConsumer(AsyncJsonWebsocketConsumer):
    """Lado servidor da conexao WebSocket do Painel de Chamada (a tela de
    TV compartilhada). So existe um grupo aqui (`painel_chamada`) porque o
    painel e unico -- todo mundo conectado nele recebe os mesmos eventos,
    disparados por core/websocket_utils.py sempre que a fila muda ou
    alguem e chamado.

    Cada metodo abaixo (paciente_chamado, fila_atualizada, painel_config)
    corresponde ao "type" do evento mandado por group_send -- o Channels
    roteia automaticamente pro metodo de mesmo nome.
    """

    GROUP_NAME = "painel_chamada"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def paciente_chamado(self, event):
        await self.send_json({
            "tipo": "paciente_chamado",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "sala": event.get("sala", ""),
            "guiche": event.get("guiche", ""),
            "timestamp": event.get("timestamp", ""),
        })

    async def fila_atualizada(self, event):
        await self.send_json({
            "tipo": "fila_atualizada",
            "fila": event.get("fila", []),
            "recent_calls": event.get("recent_calls", []),
            "timestamp": event.get("timestamp", ""),
        })

    async def painel_config(self, event):
        await self.send_json({
            "tipo": "painel_config",
            "config": event.get("config", {}),
        })
